"""
Structured Logger for SoulReel Lambda Functions.

Provides consistent JSON-formatted logging with PII redaction,
correlation ID propagation, and automatic userId extraction from
Cognito JWT claims.

Usage in a Lambda handler:

    from structured_logger import StructuredLog

    def lambda_handler(event, context):
        log = StructuredLog(event, context)
        log.info('ProcessingRequest', details={'testId': 'big-five-v1'})
        try:
            # ... business logic ...
            log.info('RequestComplete', duration_ms=elapsed, status='success')
        except ClientError as e:
            log.log_aws_error('DynamoDB', 'GetItem', e, {'TableName': t})
            return error_response(500, 'Server error', e, event, log=log)
        except Exception as e:
            log.error('UnexpectedFailure', e)
            return error_response(500, 'Server error', e, event, log=log)
"""
import json
import logging
import os
import re
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger('structured_logger')
logger.setLevel(logging.DEBUG)

# ---------------------------------------------------------------------------
# PII patterns
# ---------------------------------------------------------------------------
_EMAIL_RE = re.compile(r'[a-zA-Z0-9_.+\-]+@[a-zA-Z0-9\-]+\.[a-zA-Z0-9.\-]+')
_PHONE_RE = re.compile(
    r'(?:\+?\d{1,3}[\s\-.]?)?\(?\d{2,4}\)?[\s\-.]?\d{3,4}[\s\-.]?\d{3,4}'
)
_PII_FIELD_NAMES = frozenset({
    'email', 'phone', 'phonenumber', 'phone_number',
    'name', 'fullname', 'full_name',
    'firstname', 'first_name', 'lastname', 'last_name',
    'address', 'ssn', 'dateofbirth', 'date_of_birth',
})

_REDACTED_EMAIL = '[REDACTED_EMAIL]'
_REDACTED_PHONE = '[REDACTED_PHONE]'
_REDACTED = '[REDACTED]'

# Max recursion depth for PII redaction to prevent stack overflow
_MAX_REDACT_DEPTH = 20


class StructuredLog:
    """
    Per-invocation structured logger.

    Initialised once at the top of a Lambda handler with the event and
    context objects.  Extracts userId, correlationId, HTTP method/path,
    and environment metadata automatically.
    """

    def __init__(self, event: Optional[dict] = None, context: object = None):
        """
        Args:
            event:   The API Gateway / Lambda event dict.
            context: The Lambda context object.
        """
        self._event = event or {}
        self._context = context

        # Extract userId from Cognito JWT claims
        self._user_id = self._extract_user_id()

        # Extract correlation ID from request header
        self._correlation_id = self._extract_correlation_id()

        # HTTP context
        self._http_method = self._event.get('httpMethod', '')
        self._path = self._event.get('path', '') or self._event.get('resource', '')

        # Environment context
        self._function_name = getattr(context, 'function_name', '') if context else os.environ.get('AWS_LAMBDA_FUNCTION_NAME', '')
        self._memory_mb = int(getattr(context, 'memory_limit_in_mb', 0) if context else os.environ.get('AWS_LAMBDA_FUNCTION_MEMORY_SIZE', '0'))
        self._region = os.environ.get('AWS_REGION', os.environ.get('AWS_DEFAULT_REGION', ''))

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_user_id(self) -> str:
        """Extract userId from Cognito JWT claims in the API Gateway event."""
        try:
            return (
                self._event.get('requestContext', {})
                .get('authorizer', {})
                .get('claims', {})
                .get('sub', '')
            )
        except (AttributeError, TypeError):
            return ''

    def _extract_correlation_id(self) -> str:
        """Read X-Correlation-ID from request headers (case-insensitive)."""
        try:
            headers = self._event.get('headers') or {}
            # API Gateway may normalise header names to lowercase
            return (
                headers.get('X-Correlation-ID', '')
                or headers.get('x-correlation-id', '')
            )
        except (AttributeError, TypeError):
            return ''

    def _base_entry(self, level: str, operation: str) -> dict:
        """Build the common fields shared by every log entry."""
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': level,
            'source': 'backend',
            'operation': operation,
            'correlationId': self._correlation_id,
            'userId': self._user_id,
        }

    def _emit(self, entry: dict) -> None:
        """Serialise and write a single-line JSON log entry."""
        level = entry.get('level', 'INFO')
        line = json.dumps(entry, default=str)
        if level == 'ERROR':
            logger.error(line)
        elif level == 'WARNING':
            logger.warning(line)
        else:
            logger.info(line)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def info(
        self,
        operation: str,
        details: Optional[dict] = None,
        duration_ms: Optional[float] = None,
        status: str = 'success',
    ) -> None:
        """Emit an INFO-level structured log entry."""
        entry = self._base_entry('INFO', operation)
        entry['status'] = status
        if details is not None:
            entry['details'] = redact_pii(details)
        if duration_ms is not None:
            entry['durationMs'] = round(duration_ms, 2)
        self._emit(entry)

    def warning(
        self,
        operation: str,
        message: str,
        details: Optional[dict] = None,
    ) -> None:
        """Emit a WARNING-level structured log entry."""
        entry = self._base_entry('WARNING', operation)
        entry['message'] = message
        if details is not None:
            entry['details'] = redact_pii(details)
        self._emit(entry)

    def error(
        self,
        operation: str,
        exception: Optional[Exception] = None,
        details: Optional[dict] = None,
        message: Optional[str] = None,
    ) -> None:
        """
        Emit an ERROR-level structured log entry.

        Includes exception type, stack trace, HTTP context, environment
        context, and PII-redacted input parameters.
        """
        entry = self._base_entry('ERROR', operation)
        entry['httpMethod'] = self._http_method
        entry['path'] = self._path
        entry['environment'] = {
            'functionName': self._function_name,
            'memoryMB': self._memory_mb,
            'region': self._region,
        }

        if exception is not None:
            entry['errorType'] = type(exception).__name__
            entry['message'] = str(exception)
            entry['stackTrace'] = traceback.format_exc()
        elif message:
            entry['errorType'] = 'Error'
            entry['message'] = message
        else:
            entry['errorType'] = 'Error'
            entry['message'] = operation

        if details is not None:
            entry['inputParams'] = redact_pii(details)

        # Include a PII-redacted summary of the event body when available
        body = self._event.get('body')
        if body and 'inputParams' not in entry:
            try:
                parsed = json.loads(body) if isinstance(body, str) else body
                entry['inputParams'] = redact_pii(parsed)
            except (json.JSONDecodeError, TypeError):
                entry['inputParams'] = '[unparseable body]'

        self._emit(entry)

    def log_aws_error(
        self,
        service: str,
        operation: str,
        error: Exception,
        request_params: Optional[dict] = None,
    ) -> None:
        """
        Log a failed AWS SDK (boto3) call.

        Extracts the AWS error code and message from ClientError when
        available, and redacts PII from request parameters.
        """
        entry = self._base_entry('ERROR', f'{service}.{operation}')
        entry['httpMethod'] = self._http_method
        entry['path'] = self._path
        entry['environment'] = {
            'functionName': self._function_name,
            'memoryMB': self._memory_mb,
            'region': self._region,
        }
        entry['errorType'] = type(error).__name__
        entry['service'] = service
        entry['awsOperation'] = operation

        # Extract AWS-specific error details if available
        response = getattr(error, 'response', None)
        if response and isinstance(response, dict):
            err_info = response.get('Error', {})
            entry['errorCode'] = err_info.get('Code', '')
            entry['message'] = err_info.get('Message', str(error))
        else:
            entry['errorCode'] = ''
            entry['message'] = str(error)

        entry['stackTrace'] = traceback.format_exc()

        if request_params is not None:
            entry['requestParams'] = redact_pii(request_params)

        self._emit(entry)


# ------------------------------------------------------------------
# PII redaction (module-level function for reuse)
# ------------------------------------------------------------------

def redact_pii(data: Any, _depth: int = 0) -> Any:
    """
    Recursively walk dicts/lists and redact PII values.

    - Email addresses → [REDACTED_EMAIL]
    - Phone numbers  → [REDACTED_PHONE]
    - Known PII field names (email, phone, name, etc.) → [REDACTED]

    Returns a new object; the original is not mutated.
    """
    if _depth > _MAX_REDACT_DEPTH:
        return data

    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            key_lower = key.lower() if isinstance(key, str) else ''
            if key_lower in _PII_FIELD_NAMES:
                result[key] = _REDACTED
            else:
                result[key] = redact_pii(value, _depth + 1)
        return result

    if isinstance(data, (list, tuple)):
        return [redact_pii(item, _depth + 1) for item in data]

    if isinstance(data, str):
        return _redact_string(data)

    return data


def _redact_string(value: str) -> str:
    """Redact email addresses and phone numbers from a string value."""
    result = _EMAIL_RE.sub(_REDACTED_EMAIL, value)
    # Only apply phone redaction if the string changed (avoid false positives
    # on numeric IDs, timestamps, etc.) — phone regex is intentionally broad,
    # so we only apply it to values that look like they contain contact info.
    # We check for common phone indicators.
    if any(indicator in value.lower() for indicator in ('+', '(', 'phone', 'tel', 'mobile', 'cell')):
        result = _PHONE_RE.sub(_REDACTED_PHONE, result)
    return result
