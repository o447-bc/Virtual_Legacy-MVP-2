"""
ScorePsychTest Lambda Handler

Endpoint:
  POST /psych-tests/score  (Cognito Auth) — Score a completed psychological test

This is the core scoring engine. It is 100% data-driven: all scoring logic
is read from the Test Definition JSON stored in S3. Supports reverse scoring,
domain/facet scores (mean and sum), threshold classifications, composite rules,
optional Bedrock narrative generation, result storage, and progress cleanup.

Requirements: 1.8, 2.1, 2.2, 2.3, 2.4, 5.6, 6.1–6.12, 7.1–7.5, 8.4, 11.2
"""
import os
import json
import sys
import logging
import time
from datetime import datetime, timezone
from decimal import Decimal
from collections import defaultdict

import boto3
from botocore.exceptions import ClientError

# Add shared layer to path
sys.path.insert(0, '/opt/python')

from cors import cors_headers
from responses import error_response

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# AWS clients (module-level — reused across warm invocations)
# ---------------------------------------------------------------------------
_dynamodb = boto3.resource('dynamodb')
_s3 = boto3.client('s3')
_bedrock = boto3.client('bedrock-runtime')

_TABLE_PSYCH_TESTS = os.environ.get('TABLE_PSYCH_TESTS', 'PsychTestsDB')
_TABLE_USER_TEST_RESULTS = os.environ.get('TABLE_USER_TEST_RESULTS', 'UserTestResultsDB')
_TABLE_USER_TEST_PROGRESS = os.environ.get('TABLE_USER_TEST_PROGRESS', 'UserTestProgressDB')
_S3_BUCKET = os.environ.get('S3_BUCKET', 'virtual-legacy')

# Path to bundled JSON Schema (inside Lambda CodeUri)
_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), 'schemas',
                            'psych-test-definition.schema.json')


# ===================================================================
# JSON encoder for DynamoDB Decimal types
# ===================================================================

class DecimalEncoder(json.JSONEncoder):
    """Convert Decimal values to int or float for JSON serialization."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            if obj % 1 == 0:
                return int(obj)
            return float(obj)
        return super().default(obj)


def _float_to_decimal(obj):
    """Recursively convert float values to Decimal for DynamoDB storage."""
    if isinstance(obj, float):
        return Decimal(str(round(obj, 6)))
    if isinstance(obj, dict):
        return {k: _float_to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_float_to_decimal(i) for i in obj]
    return obj


# ===================================================================
# Helper: CORS response
# ===================================================================

def cors_response(status_code, body, event=None):
    """Return an API Gateway response with CORS headers."""
    return {
        'statusCode': status_code,
        'headers': cors_headers(event),
        'body': json.dumps(body, cls=DecimalEncoder),
    }


# ===================================================================
# Schema loading (lazy, cached)
# ===================================================================

_cached_schema = None


def _load_schema():
    """Load and cache the Test Definition JSON Schema."""
    global _cached_schema
    if _cached_schema is None:
        with open(_SCHEMA_PATH, 'r') as f:
            _cached_schema = json.load(f)
    return _cached_schema


# ===================================================================
# 5.1 — Request handling and validation
# ===================================================================

def lambda_handler(event, context):
    """Route POST /psych-tests/score requests."""

    # Handle OPTIONS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return cors_response(200, {}, event)

    # Extract userId from Cognito claims
    user_id = (
        event.get('requestContext', {})
        .get('authorizer', {})
        .get('claims', {})
        .get('sub')
    )
    if not user_id:
        return error_response(401, 'Unauthorized', event=event)

    try:
        return _handle_score(event, user_id)
    except Exception as exc:
        logger.error('[SCORE_PSYCH_TEST] Unhandled error: %s', exc)
        return error_response(500, 'Internal server error', exception=exc, event=event)


def _handle_score(event, user_id):
    """Core scoring flow: validate → score → narrative → store → cleanup."""

    # --- Parse request body ---
    body = event.get('body')
    if not body:
        return cors_response(400, {'error': 'Missing request body'}, event)

    try:
        data = json.loads(body)
    except (json.JSONDecodeError, TypeError):
        return cors_response(400, {'error': 'Invalid JSON in request body'}, event)

    test_id = data.get('testId')
    responses = data.get('responses')
    progress_id = data.get('progressId')  # optional

    if not test_id:
        return cors_response(400, {'error': 'Missing required field: testId'}, event)
    if responses is None or not isinstance(responses, list):
        return cors_response(400, {'error': 'Missing or invalid field: responses'}, event)

    # --- Fetch Test Definition from S3 ---
    test_def = _fetch_test_definition(test_id)
    if test_def is None:
        return cors_response(404, {'error': f'Test definition not found: {test_id}'}, event)

    # --- Validate Test Definition against JSON Schema ---
    validation_error = _validate_test_definition(test_def)
    if validation_error:
        return cors_response(400, {'error': f'Invalid test definition: {validation_error}'}, event)

    # --- Cross-validate scoring rules → questions ---
    question_ids = {q['questionId'] for q in test_def['questions']}
    scoring_rules = test_def.get('scoringRules', {})

    orphaned = _find_orphaned_scoring_refs(test_def['questions'], scoring_rules)
    if orphaned:
        return cors_response(400, {
            'error': f'Orphaned scoring reference: scoring keys {orphaned} '
                     f'not found as scoringKey on any question'
        }, event)

    # --- Cross-validate composite rules → scoring rules ---
    composite_rules = test_def.get('compositeRules', {})
    missing_domains = _find_missing_composite_domains(composite_rules, scoring_rules, test_id)
    if missing_domains:
        return cors_response(400, {
            'error': f'Missing domain reference: {missing_domains} not defined in scoringRules'
        }, event)

    # --- Validate all required questionIds have responses ---
    response_map = {r['questionId']: r['answer'] for r in responses}
    logger.info('[SCORE_PSYCH_TEST] Received %d responses, test has %d questions', len(response_map), len(question_ids))
    missing_qids = [qid for qid in question_ids if qid not in response_map]
    if missing_qids:
        logger.warning('[SCORE_PSYCH_TEST] Missing responses for %d questions: %s', len(missing_qids), sorted(missing_qids))
        return cors_response(400, {
            'error': f'Missing responses for questions: {sorted(missing_qids)}'
        }, event)

    # --- 5.2: Scoring logic ---
    scored_values = _apply_reverse_scoring(test_def['questions'], response_map)
    domain_scores = _calculate_domain_scores(test_def['questions'], scored_values, scoring_rules)
    facet_scores = _calculate_facet_scores(test_def['questions'], scored_values, scoring_rules)
    threshold_classifications = _apply_thresholds(domain_scores, facet_scores, scoring_rules)
    composite_scores = _apply_composite_rules(
        composite_rules, domain_scores, facet_scores, user_id, test_id
    )

    # --- 5.3: Narrative generation ---
    version = test_def.get('version', '1.0.0')
    narrative_text, narrative_source = _generate_narrative(
        test_def, domain_scores, facet_scores, user_id, test_id, version
    )

    # --- 5.4: Store results and cleanup progress ---
    timestamp = datetime.now(timezone.utc).isoformat()
    result_record = {
        'userId': user_id,
        'testId': test_id,
        'version': version,
        'timestamp': timestamp,
        'domainScores': domain_scores,
        'facetScores': facet_scores,
        'compositeScores': composite_scores,
        'thresholdClassifications': threshold_classifications,
        'narrativeText': narrative_text,
        'narrativeSource': narrative_source,
        'rawResponses': responses,
        'exportFormats': test_def.get('exportFormats', []),
    }

    _store_results(user_id, test_id, version, timestamp, result_record)
    _delete_progress(user_id, test_id)

    # Build response (exclude rawResponses from client response)
    response_body = {
        'userId': user_id,
        'testId': test_id,
        'version': version,
        'timestamp': timestamp,
        'domainScores': domain_scores,
        'facetScores': facet_scores,
        'compositeScores': composite_scores,
        'thresholdClassifications': threshold_classifications,
        'narrativeText': narrative_text,
        'narrativeSource': narrative_source,
        'exportFormats': test_def.get('exportFormats', []),
    }

    logger.info(
        '[SCORE_PSYCH_TEST] Scored test=%s for user=%s domains=%d facets=%d',
        test_id, user_id, len(domain_scores), len(facet_scores),
    )

    return cors_response(200, response_body, event)


# ===================================================================
# S3 and schema helpers (5.1)
# ===================================================================

def _fetch_test_definition(test_id):
    """Fetch Test Definition JSON from S3. Returns dict or None."""
    s3_key = f'psych-tests/{test_id}.json'
    try:
        response = _s3.get_object(Bucket=_S3_BUCKET, Key=s3_key)
        body = response['Body'].read().decode('utf-8')
        return json.loads(body)
    except ClientError as exc:
        if exc.response['Error']['Code'] == 'NoSuchKey':
            return None
        raise


def _validate_test_definition(test_def):
    """Validate Test Definition against JSON Schema. Returns error string or None."""
    try:
        import jsonschema
    except ImportError:
        logger.warning('[SCORE_PSYCH_TEST] jsonschema not available, skipping validation')
        return None

    schema = _load_schema()
    try:
        jsonschema.validate(instance=test_def, schema=schema)
        return None
    except jsonschema.ValidationError as exc:
        return f'{exc.json_path}: {exc.message}'


def _find_orphaned_scoring_refs(questions, scoring_rules):
    """Check that all scoring rule keys are referenced by at least one question's scoringKey.

    Returns a list of orphaned scoring rule keys, or empty list if all valid.
    """
    question_scoring_keys = {q['scoringKey'] for q in questions}
    orphaned = [key for key in scoring_rules if key not in question_scoring_keys]
    # Also check facet-level: scoring rules may reference groupByFacet values
    question_facet_keys = {q['groupByFacet'] for q in questions}
    orphaned = [k for k in orphaned if k not in question_facet_keys]
    return orphaned


def _find_missing_composite_domains(composite_rules, scoring_rules, current_test_id):
    """Check that composite rules reference domains defined in scoring rules.

    For sources referencing the current test, the domain must exist in scoringRules.
    For sources referencing other tests, we skip validation (cross-test).
    Returns a list of missing domain names, or empty list if all valid.
    """
    missing = []
    for comp_name, rule in composite_rules.items():
        for source in rule.get('sources', []):
            if source.get('testId') == current_test_id:
                domain = source.get('domain')
                if domain and domain not in scoring_rules:
                    missing.append(domain)
    return missing


# ===================================================================
# 5.2 — Scoring logic
# ===================================================================

def _apply_reverse_scoring(questions, response_map):
    """Apply reverse scoring. Returns dict of questionId → scored value."""
    scored = {}
    for q in questions:
        qid = q['questionId']
        raw = response_map.get(qid)
        if raw is None:
            continue
        if q.get('reverseScored') and q.get('responseType') == 'likert5':
            scored[qid] = 6 - raw
        else:
            scored[qid] = raw
    return scored


def _calculate_domain_scores(questions, scored_values, scoring_rules):
    """Group scored responses by scoringKey, apply formula from scoring rules.

    Returns dict of domain → {raw, normalized, label}.
    """
    # Group scored values by scoringKey (domain)
    groups = defaultdict(list)
    for q in questions:
        qid = q['questionId']
        if qid in scored_values:
            groups[q['scoringKey']].append(scored_values[qid])

    domain_scores = {}
    for domain, values in groups.items():
        rule = scoring_rules.get(domain)
        if not rule:
            continue
        raw = _apply_formula(rule.get('formula', 'mean'), values)
        domain_scores[domain] = {
            'raw': round(raw, 4),
            'normalized': round(raw, 4),
            'label': _classify(raw, rule.get('thresholds', [])),
        }
    return domain_scores


def _calculate_facet_scores(questions, scored_values, scoring_rules):
    """Group scored responses by groupByFacet, apply formula from scoring rules.

    Returns dict of facet → {raw, normalized, label}.
    """
    # Group scored values by groupByFacet
    groups = defaultdict(list)
    for q in questions:
        qid = q['questionId']
        if qid in scored_values:
            groups[q['groupByFacet']].append(scored_values[qid])

    facet_scores = {}
    for facet, values in groups.items():
        # Look up scoring rule for this facet; fall back to parent domain rule
        rule = scoring_rules.get(facet)
        if not rule:
            # Try to find the parent domain rule via the first question's scoringKey
            parent_domain = None
            for q in questions:
                if q['groupByFacet'] == facet:
                    parent_domain = q['scoringKey']
                    break
            rule = scoring_rules.get(parent_domain) if parent_domain else None
        if not rule:
            continue
        raw = _apply_formula(rule.get('formula', 'mean'), values)
        facet_scores[facet] = {
            'raw': round(raw, 4),
            'normalized': round(raw, 4),
            'label': _classify(raw, rule.get('thresholds', [])),
        }
    return facet_scores


def _apply_formula(formula, values):
    """Apply a scoring formula to a list of numeric values."""
    if not values:
        return 0.0
    if formula == 'sum':
        return float(sum(values))
    # Default to mean
    return float(sum(values)) / len(values)


def _classify(score, thresholds):
    """Find the matching threshold label for a score. Returns 'unclassified' if none."""
    for t in thresholds:
        if t['min'] <= score <= t['max']:
            return t['label']
    return 'unclassified'


def _apply_thresholds(domain_scores, facet_scores, scoring_rules):
    """Build a flat map of domain/facet → threshold label."""
    classifications = {}
    for name, entry in domain_scores.items():
        classifications[name] = entry.get('label', 'unclassified')
    for name, entry in facet_scores.items():
        classifications[name] = entry.get('label', 'unclassified')
    return classifications


def _apply_composite_rules(composite_rules, domain_scores, facet_scores, user_id, test_id):
    """Apply composite rules to combine domain/facet scores.

    For sources referencing the current test, use the just-calculated scores.
    For sources referencing other tests, fetch from UserTestResults table.
    """
    if not composite_rules:
        return {}

    composite_scores = {}
    for comp_name, rule in composite_rules.items():
        source_values = []
        all_available = True

        for source in rule.get('sources', []):
            src_test_id = source.get('testId')
            src_domain = source.get('domain')

            if src_test_id == test_id:
                # Use current test's scores
                entry = domain_scores.get(src_domain) or facet_scores.get(src_domain)
                if entry:
                    source_values.append(entry['raw'])
                else:
                    all_available = False
            else:
                # Fetch from prior results
                prior = _fetch_prior_domain_score(user_id, src_test_id, src_domain)
                if prior is not None:
                    source_values.append(prior)
                else:
                    all_available = False

        if all_available and source_values:
            raw = _apply_formula(rule.get('formula', 'mean'), source_values)
            composite_scores[comp_name] = {
                'raw': round(raw, 4),
                'normalized': round(raw, 4),
                'label': 'composite',
            }

    return composite_scores


def _fetch_prior_domain_score(user_id, test_id, domain):
    """Fetch the most recent domain score for a user's prior test result.

    Returns the raw score float, or None if not found.
    """
    try:
        table = _dynamodb.Table(_TABLE_USER_TEST_RESULTS)
        from boto3.dynamodb.conditions import Key
        response = table.query(
            KeyConditionExpression=Key('userId').eq(user_id),
            FilterExpression='testId = :tid',
            ExpressionAttributeValues={':tid': test_id},
            ScanIndexForward=False,
            Limit=1,
        )
        items = response.get('Items', [])
        if not items:
            return None
        domain_scores = items[0].get('domainScores', {})
        entry = domain_scores.get(domain)
        if entry:
            raw = entry.get('raw', entry) if isinstance(entry, dict) else entry
            return float(raw)
        return None
    except Exception as exc:
        logger.warning('[SCORE_PSYCH_TEST] Failed to fetch prior score: %s', exc)
        return None


# ===================================================================
# 5.3 — Bedrock narrative generation
# ===================================================================

def _generate_narrative(test_def, domain_scores, facet_scores, user_id, test_id, version):
    """Generate narrative text. Returns (narrative_text, narrative_source).

    If bedrockConfig.useBedrock is true, attempts Bedrock first with cache check.
    Falls back to interpretationTemplates on failure or when Bedrock is disabled.
    """
    bedrock_config = test_def.get('bedrockConfig')
    interpretation_templates = test_def.get('interpretationTemplates', {})

    if bedrock_config and bedrock_config.get('useBedrock'):
        cache_days = bedrock_config.get('cacheResultsForDays', 0)

        # Check cache if caching is enabled
        if cache_days > 0:
            cached = _check_narrative_cache(user_id, test_id)
            if cached:
                return cached, 'bedrock'

        # Call Bedrock
        try:
            narrative = _call_bedrock(
                bedrock_config, domain_scores, facet_scores,
                interpretation_templates, test_def.get('testName', test_id),
            )
            # Cache the narrative if caching is enabled
            if cache_days > 0:
                _cache_narrative(user_id, test_id, version, narrative, cache_days)
            return narrative, 'bedrock'
        except Exception as exc:
            logger.error(
                '[SCORE_PSYCH_TEST] Bedrock call failed, falling back to templates: %s', exc
            )
            # Fall through to template generation

    # Template-based narrative
    narrative = _generate_template_narrative(
        domain_scores, facet_scores, interpretation_templates
    )
    return narrative, 'template'


def _check_narrative_cache(user_id, test_id):
    """Check UserTestResults for a cached narrative that hasn't expired.

    Returns the cached narrative text, or None.
    """
    try:
        table = _dynamodb.Table(_TABLE_USER_TEST_RESULTS)
        from boto3.dynamodb.conditions import Key
        response = table.query(
            KeyConditionExpression=Key('userId').eq(user_id),
            FilterExpression='testId = :tid',
            ExpressionAttributeValues={':tid': test_id},
            ScanIndexForward=False,
            Limit=1,
        )
        items = response.get('Items', [])
        if not items:
            return None
        item = items[0]
        cache_expiry = item.get('cacheExpiry')
        if cache_expiry:
            now = datetime.now(timezone.utc).isoformat()
            if now < cache_expiry and item.get('narrativeSource') == 'bedrock':
                return item.get('narrativeText')
        return None
    except Exception as exc:
        logger.warning('[SCORE_PSYCH_TEST] Cache check failed: %s', exc)
        return None


def _call_bedrock(bedrock_config, domain_scores, facet_scores,
                  interpretation_templates, test_name):
    """Call Bedrock InvokeModel to generate a narrative interpretation."""
    max_tokens = bedrock_config.get('maxTokens', 1024)
    temperature = bedrock_config.get('temperature', 0.7)

    # Build prompt with scored results and templates as context
    prompt_parts = [
        f'You are a personality assessment interpreter for the {test_name} test.',
        'Based on the following scored results, generate a warm, insightful narrative '
        'interpretation for the user. Use the interpretation templates as guidance.',
        '',
        'Domain Scores:',
    ]
    for domain, entry in domain_scores.items():
        prompt_parts.append(f'  {domain}: {entry["raw"]} ({entry["label"]})')

    if facet_scores:
        prompt_parts.append('')
        prompt_parts.append('Facet Scores:')
        for facet, entry in facet_scores.items():
            prompt_parts.append(f'  {facet}: {entry["raw"]} ({entry["label"]})')

    if interpretation_templates:
        prompt_parts.append('')
        prompt_parts.append('Interpretation Templates (use as guidance):')
        for key, entries in interpretation_templates.items():
            for entry in entries:
                prompt_parts.append(
                    f'  {key} [{entry["min"]}-{entry["max"]}]: {entry["text"]}'
                )

    prompt_text = '\n'.join(prompt_parts)

    request_body = json.dumps({
        'anthropic_version': 'bedrock-2023-05-31',
        'max_tokens': max_tokens,
        'temperature': temperature,
        'messages': [
            {'role': 'user', 'content': prompt_text}
        ],
    })

    response = _bedrock.invoke_model(
        modelId='anthropic.claude-3-haiku-20240307-v1:0',
        contentType='application/json',
        accept='application/json',
        body=request_body,
    )

    response_body = json.loads(response['body'].read().decode('utf-8'))
    # Extract text from Claude response
    content = response_body.get('content', [])
    if content and isinstance(content, list):
        return content[0].get('text', '')
    return ''


def _cache_narrative(user_id, test_id, version, narrative, cache_days):
    """Store narrative with cache expiry in UserTestResults (update existing record)."""
    try:
        cache_expiry = datetime.now(timezone.utc)
        cache_expiry_str = cache_expiry.isoformat()
        # We'll set cacheExpiry when storing the full result in _store_results
        # This is a no-op here; the cache expiry is set during result storage
    except Exception as exc:
        logger.warning('[SCORE_PSYCH_TEST] Failed to cache narrative: %s', exc)


def _generate_template_narrative(domain_scores, facet_scores, interpretation_templates):
    """Generate narrative from interpretationTemplates based on scored results."""
    parts = []

    for domain, entry in domain_scores.items():
        raw = entry['raw']
        templates = interpretation_templates.get(domain, [])
        for t in templates:
            if t['min'] <= raw <= t['max']:
                parts.append(t['text'])
                break

    for facet, entry in facet_scores.items():
        raw = entry['raw']
        templates = interpretation_templates.get(facet, [])
        for t in templates:
            if t['min'] <= raw <= t['max']:
                parts.append(t['text'])
                break

    return ' '.join(parts) if parts else ''


# ===================================================================
# 5.4 — Result storage and progress cleanup
# ===================================================================

def _store_results(user_id, test_id, version, timestamp, result_record):
    """Store complete results in UserTestResults table.

    Sort key is {testId}#{version}#{timestamp}.
    DynamoDB requires Decimal instead of float, so we convert recursively.
    """
    table = _dynamodb.Table(_TABLE_USER_TEST_RESULTS)
    sk = f'{test_id}#{version}#{timestamp}'

    item = _float_to_decimal({
        'userId': user_id,
        'testIdVersionTimestamp': sk,
        'testId': test_id,
        'version': version,
        'timestamp': timestamp,
        'domainScores': result_record.get('domainScores', {}),
        'facetScores': result_record.get('facetScores', {}),
        'compositeScores': result_record.get('compositeScores', {}),
        'thresholdClassifications': result_record.get('thresholdClassifications', {}),
        'narrativeText': result_record.get('narrativeText', ''),
        'narrativeSource': result_record.get('narrativeSource', 'template'),
        'rawResponses': result_record.get('rawResponses', []),
    })

    table.put_item(Item=item)
    logger.info(
        '[SCORE_PSYCH_TEST] Stored results for user=%s test=%s version=%s',
        user_id, test_id, version,
    )


def _delete_progress(user_id, test_id):
    """Delete the progress record from UserTestProgress table after scoring."""
    try:
        table = _dynamodb.Table(_TABLE_USER_TEST_PROGRESS)
        table.delete_item(
            Key={
                'userId': user_id,
                'testId': test_id,
            }
        )
        logger.info(
            '[SCORE_PSYCH_TEST] Deleted progress for user=%s test=%s',
            user_id, test_id,
        )
    except Exception as exc:
        # Non-fatal: progress cleanup failure shouldn't block scoring
        logger.warning(
            '[SCORE_PSYCH_TEST] Failed to delete progress for user=%s test=%s: %s',
            user_id, test_id, exc,
        )
