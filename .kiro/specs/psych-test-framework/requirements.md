# Requirements Document

## Introduction

Soul Reel's Section 3 ("Values and Emotions Deep Dive") introduces a scalable psychological testing framework that allows legacy makers to complete validated open-source personality assessments (IPIP-NEO-60, OEJTS, Personality-Based Emotional Intelligence Test) and receive a unified "Legacy Portrait" combining results across tests. The framework is fully data-driven: new tests are added by uploading a JSON definition file to S3 with zero Lambda code changes. Results feed into the existing content path system and can optionally include AI-generated narrative interpretations via AWS Bedrock.

## Glossary

- **Test_Definition**: A JSON file stored in S3 at `psych-tests/{testId}.json` that fully describes a psychological test including questions, scoring rules, interpretation templates, and configuration options.
- **Test_Definition_Schema**: The reusable JSON schema that all Test_Definition files must conform to, enabling any new test to be added without code changes.
- **ScorePsychTest_Lambda**: A single generic AWS Lambda function that scores any psychological test by loading its Test_Definition from S3 and applying the embedded scoring rules dynamically.
- **Legacy_Portrait**: A composite personality profile combining scored results from multiple psychological tests into a unified narrative for the legacy maker.
- **PsychTests_Table**: A DynamoDB table storing test metadata records (testId, testName, version, status, S3 path) used for listing available tests and version management.
- **UserTestProgress_Table**: A DynamoDB table storing in-progress test responses with TTL, enabling users to save and resume incomplete tests.
- **UserTestResults_Table**: A DynamoDB table storing completed test results including domain scores, facet scores, composite scores, and interpretation text.
- **Admin_Conversion_Script**: A backend process that reads a Test_Definition JSON and generates individual question records compatible with the existing admin question management flow.
- **Test_Taking_UI**: A React/TypeScript frontend component that dynamically renders any psychological test based on its Test_Definition, handling consent, questions, progress, and results display.
- **Consent_Block**: A required screen shown before test questions that includes a title, body text, and a required checkbox the user must accept before proceeding.
- **Scoring_Rules**: The embedded rules within a Test_Definition that define how raw responses are converted into domain scores, facet scores, and thresholds.
- **Composite_Rules**: Rules within a Test_Definition that define how scores from multiple domains or tests are combined to produce the Legacy_Portrait.
- **Interpretation_Templates**: Score-range-to-narrative-string mappings within a Test_Definition used to generate human-readable result descriptions.
- **Video_Prompt_Trigger**: A configurable template string in the Test_Definition that triggers video recording prompts at specified intervals during test-taking.
- **Bedrock_Config**: An optional configuration block in the Test_Definition that enables AI-generated narrative interpretation via AWS Bedrock.

## Requirements

### Requirement 1: Test Definition Schema

**User Story:** As a system administrator, I want a single reusable JSON schema for defining any psychological test, so that new tests can be added by uploading a JSON file to S3 without modifying Lambda code.

#### Acceptance Criteria

1. THE Test_Definition_Schema SHALL define the following top-level fields: testId (string), testName (string), description (string), version (string), previousVersionMapping (object), estimatedMinutes (number), consentBlock (object), disclaimerText (string), questions (array), scoringRules (object), compositeRules (object), interpretationTemplates (object), bedrockConfig (object, optional), videoPromptTrigger (string), saveProgressEnabled (boolean), analyticsEnabled (boolean), and exportFormats (array of strings).
2. THE Test_Definition_Schema SHALL define each question object with the fields: questionId (string), text (string), responseType (one of "likert5", "bipolar5", "multipleChoice"), options (array), reverseScored (boolean), scoringKey (string), groupByFacet (string), pageBreakAfter (boolean), accessibilityHint (string), and videoPromptFrequency (number, optional).
3. THE Test_Definition_Schema SHALL define the consentBlock object with the fields: title (string), bodyText (string), and requiredCheckboxLabel (string).
4. THE Test_Definition_Schema SHALL define the scoringRules object with domain-level and facet-level entries, each containing formula (string), thresholds (array of objects with min, max, and label), and lookupTables (object, optional).
5. THE Test_Definition_Schema SHALL define the compositeRules object with entries that reference domain or facet scores from one or more tests and specify a combining formula for Legacy_Portrait generation.
6. THE Test_Definition_Schema SHALL define the interpretationTemplates object as a mapping of score ranges to narrative strings, keyed by domain or facet name.
7. THE Test_Definition_Schema SHALL define the bedrockConfig object with the fields: useBedrock (boolean), maxTokens (number), temperature (number), and cacheResultsForDays (number).
8. WHEN a Test_Definition JSON file is uploaded to S3 at `psych-tests/{testId}.json`, THE ScorePsychTest_Lambda SHALL be able to load and process the test without any code changes.
9. THE Test_Definition_Schema SHALL be documented as a JSON Schema file stored in the repository at `SamLambda/schemas/psych-test-definition.schema.json`.
10. FOR ALL valid Test_Definition JSON files, parsing the JSON then serializing it back to JSON then parsing again SHALL produce an equivalent object (round-trip property).

### Requirement 2: Test Definition Validation

**User Story:** As a system administrator, I want uploaded test definitions to be validated against the schema, so that malformed test files are rejected before they can cause scoring errors.

#### Acceptance Criteria

1. WHEN a Test_Definition JSON file is loaded by the ScorePsychTest_Lambda, THE ScorePsychTest_Lambda SHALL validate the file against the Test_Definition_Schema before processing.
2. IF a Test_Definition JSON file fails schema validation, THEN THE ScorePsychTest_Lambda SHALL return a 400 response with a descriptive error message identifying the validation failure.
3. WHEN a Test_Definition contains a scoringRules formula referencing a questionId not present in the questions array, THE ScorePsychTest_Lambda SHALL return a 400 response indicating the orphaned reference.
4. WHEN a Test_Definition contains a compositeRules entry referencing a domain not defined in scoringRules, THE ScorePsychTest_Lambda SHALL return a 400 response indicating the missing domain reference.

### Requirement 3: Admin Test Import

**User Story:** As a system administrator, I want to import psychological test definitions through the existing admin interface, so that I can manage tests using the same workflow I use for regular questions.

#### Acceptance Criteria

1. WHEN an administrator uploads a Test_Definition JSON file via the admin interface, THE Admin_Conversion_Script SHALL parse the file and generate individual question records in the allQuestionDB table.
2. WHEN the Admin_Conversion_Script generates question records, THE Admin_Conversion_Script SHALL set the questionType field to the testId from the Test_Definition and tag each record with the corresponding facet from groupByFacet.
3. WHEN a Test_Definition JSON file is imported, THE Admin_Conversion_Script SHALL create a metadata record in the PsychTests_Table containing testId, testName, version, status, estimatedMinutes, s3Path, and createdAt.
4. IF a Test_Definition with the same testId and version already exists in the PsychTests_Table, THEN THE Admin_Conversion_Script SHALL return an error indicating a duplicate version.
5. WHEN a new version of an existing test is imported, THE Admin_Conversion_Script SHALL store the previousVersionMapping from the Test_Definition to enable backward compatibility.

### Requirement 4: PsychTests DynamoDB Table

**User Story:** As a system administrator, I want a dedicated DynamoDB table for psychological test metadata, so that the system can list available tests and manage test versions.

#### Acceptance Criteria

1. THE PsychTests_Table SHALL use testId as the partition key and version as the sort key.
2. THE PsychTests_Table SHALL include a Global Secondary Index named status-index with status as the partition key and createdAt as the sort key, enabling queries for all active tests.
3. THE PsychTests_Table SHALL be defined in `SamLambda/template.yml` with PAY_PER_REQUEST billing, KMS encryption using the existing DataEncryptionKey, and point-in-time recovery enabled.
4. THE PsychTests_Table SHALL store the fields: testId, version, testName, description, estimatedMinutes, status (active/inactive/archived), s3Path, previousVersionMapping, and createdAt.

### Requirement 5: UserTestProgress Table and Resume

**User Story:** As a legacy maker, I want my in-progress test responses to be saved automatically, so that I can resume a test later without losing my answers.

#### Acceptance Criteria

1. THE UserTestProgress_Table SHALL use userId as the partition key and testId as the sort key.
2. THE UserTestProgress_Table SHALL include a TTL attribute named expiresAt set to 30 days from the last update, automatically removing stale progress records.
3. THE UserTestProgress_Table SHALL be defined in `SamLambda/template.yml` with PAY_PER_REQUEST billing, KMS encryption using the existing DataEncryptionKey, and point-in-time recovery enabled.
4. WHEN a user submits partial responses for a test with saveProgressEnabled set to true, THE Test_Taking_UI SHALL send the responses to a SaveTestProgress API endpoint that stores them in the UserTestProgress_Table.
5. WHEN a user opens a test for which a progress record exists in the UserTestProgress_Table, THE Test_Taking_UI SHALL load the saved responses and resume from the last answered question.
6. WHEN a user completes a test, THE ScorePsychTest_Lambda SHALL delete the corresponding progress record from the UserTestProgress_Table.

### Requirement 6: Scalable Scoring Engine

**User Story:** As a legacy maker, I want my test responses to be scored accurately using the rules embedded in the test definition, so that I receive a valid personality profile.

#### Acceptance Criteria

1. THE ScorePsychTest_Lambda SHALL accept a request body containing userId, testId, responses (array of questionId/answer pairs), and an optional progressId.
2. WHEN the ScorePsychTest_Lambda receives a scoring request, THE ScorePsychTest_Lambda SHALL fetch the Test_Definition from S3 at `psych-tests/{testId}.json`.
3. WHEN the ScorePsychTest_Lambda processes responses, THE ScorePsychTest_Lambda SHALL apply reverse scoring to questions where reverseScored is true before calculating domain and facet scores.
4. THE ScorePsychTest_Lambda SHALL calculate domain scores by applying the formula defined in scoringRules for each domain, using the scored responses grouped by scoringKey.
5. THE ScorePsychTest_Lambda SHALL calculate facet scores by applying the formula defined in scoringRules for each facet, using the scored responses grouped by groupByFacet.
6. THE ScorePsychTest_Lambda SHALL apply threshold classifications to each domain and facet score using the thresholds array defined in scoringRules.
7. WHEN the Test_Definition includes compositeRules, THE ScorePsychTest_Lambda SHALL apply the composite formulas to generate Legacy_Portrait scores combining results across domains or tests.
8. WHEN the Test_Definition includes a previousVersionMapping and the user has prior results from an older version, THE ScorePsychTest_Lambda SHALL use the mapping to align question IDs for comparison.
9. THE ScorePsychTest_Lambda SHALL store the complete results (domain scores, facet scores, composite scores, thresholds, raw responses, testId, version, and timestamp) in the UserTestResults_Table.
10. THE ScorePsychTest_Lambda SHALL be defined in `SamLambda/template.yml` with IAM policies granting s3:GetObject on the psych-tests S3 prefix, dynamodb:GetItem and dynamodb:PutItem on PsychTests_Table, UserTestProgress_Table, and UserTestResults_Table, and dynamodb:DeleteItem on UserTestProgress_Table.
11. THE ScorePsychTest_Lambda SHALL include `import os` at the top of its handler file and read the ALLOWED_ORIGIN from `os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')` for CORS headers on every response.
12. FOR ALL sets of valid responses to a test, scoring the responses then re-scoring the same responses SHALL produce identical domain scores, facet scores, and threshold classifications (idempotence property).

### Requirement 7: Bedrock Narrative Generation

**User Story:** As a legacy maker, I want AI-generated narrative interpretations of my test results, so that I receive a personalized and readable summary of my personality profile.

#### Acceptance Criteria

1. WHEN the Test_Definition has bedrockConfig.useBedrock set to true, THE ScorePsychTest_Lambda SHALL call AWS Bedrock to generate a narrative interpretation using the scored results and interpretationTemplates as context.
2. WHEN calling AWS Bedrock, THE ScorePsychTest_Lambda SHALL use the maxTokens and temperature values from bedrockConfig.
3. WHEN bedrockConfig.cacheResultsForDays is greater than zero, THE ScorePsychTest_Lambda SHALL check the UserTestResults_Table for a cached narrative before calling Bedrock, and store the generated narrative with a cacheExpiry timestamp.
4. IF the Bedrock API call fails, THEN THE ScorePsychTest_Lambda SHALL fall back to the static interpretationTemplates and include a flag in the result indicating the narrative was template-generated.
5. THE ScorePsychTest_Lambda SHALL have an IAM policy granting bedrock:InvokeModel on the configured Bedrock model ARN.

### Requirement 8: UserTestResults Table

**User Story:** As a legacy maker, I want my completed test results stored securely, so that I can view them later and they contribute to my Legacy Portrait.

#### Acceptance Criteria

1. THE UserTestResults_Table SHALL use userId as the partition key and a composite sort key of `{testId}#{version}#{timestamp}`.
2. THE UserTestResults_Table SHALL include a Global Secondary Index named testId-index with testId as the partition key and timestamp as the sort key, enabling queries for all results of a specific test.
3. THE UserTestResults_Table SHALL be defined in `SamLambda/template.yml` with PAY_PER_REQUEST billing, KMS encryption using the existing DataEncryptionKey, and point-in-time recovery enabled.
4. THE UserTestResults_Table SHALL store the fields: userId, testId, version, timestamp, domainScores (map), facetScores (map), compositeScores (map), thresholdClassifications (map), narrativeText (string, optional), narrativeSource (string: "bedrock" or "template"), rawResponses (list), and exportPaths (map, optional).

### Requirement 9: Interpretation and Export

**User Story:** As a legacy maker, I want to export my test results in multiple formats, so that I can share my personality profile with family or professionals.

#### Acceptance Criteria

1. WHEN a user requests an export of test results, THE ScorePsychTest_Lambda SHALL generate the export in the requested format from the exportFormats array in the Test_Definition (PDF, JSON, or CSV).
2. THE ScorePsychTest_Lambda SHALL store generated export files in S3 at `psych-exports/{userId}/{testId}/{timestamp}.{format}` and record the S3 path in the exportPaths field of the UserTestResults_Table.
3. WHEN a user requests a PDF export, THE ScorePsychTest_Lambda SHALL generate a document containing the test name, date, domain scores with threshold labels, facet scores, and the narrative interpretation text.
4. WHEN a user requests a JSON export, THE ScorePsychTest_Lambda SHALL generate a file containing the complete result record from the UserTestResults_Table excluding rawResponses.
5. WHEN a user requests a CSV export, THE ScorePsychTest_Lambda SHALL generate a file with columns for domain/facet name, raw score, threshold label, and percentile (where available).
6. THE ScorePsychTest_Lambda SHALL have an IAM policy granting s3:PutObject on the `psych-exports/` S3 prefix for storing export files.
7. THE ScorePsychTest_Lambda SHALL generate pre-signed S3 URLs for export file downloads with a 24-hour expiry.

### Requirement 10: Frontend Test-Taking UI

**User Story:** As a legacy maker, I want a dynamic test-taking interface that guides me through any psychological test, so that I can complete assessments comfortably on any device.

#### Acceptance Criteria

1. WHEN a user navigates to a psychological test, THE Test_Taking_UI SHALL fetch the Test_Definition from the API and render the Consent_Block before displaying any questions.
2. WHEN the user accepts the Consent_Block checkbox and clicks proceed, THE Test_Taking_UI SHALL display questions according to the responseType field: Likert 5-point scale for "likert5", bipolar 5-point scale for "bipolar5", and radio buttons for "multipleChoice".
3. THE Test_Taking_UI SHALL display a progress bar showing the percentage of questions answered out of the total question count.
4. WHEN a question has pageBreakAfter set to true, THE Test_Taking_UI SHALL display a page transition before showing the next question.
5. WHEN questions share the same groupByFacet value, THE Test_Taking_UI SHALL group those questions visually under a facet heading.
6. THE Test_Taking_UI SHALL render each question with the accessibilityHint value as an aria-describedby attribute for screen reader support.
7. WHEN the Test_Definition has saveProgressEnabled set to true, THE Test_Taking_UI SHALL auto-save responses to the SaveTestProgress API endpoint every 30 seconds and on page visibility change.
8. WHEN a question has a videoPromptFrequency value and the current question index is a multiple of that value, THE Test_Taking_UI SHALL display a video recording prompt using the videoPromptTrigger template from the Test_Definition.
9. WHEN the user completes all questions and submits, THE Test_Taking_UI SHALL POST the responses to the ScorePsychTest API endpoint and display a loading state during scoring.
10. WHEN scoring completes, THE Test_Taking_UI SHALL display the Legacy_Portrait results page showing domain scores, facet breakdowns, threshold labels, narrative interpretation, and export buttons for each format in exportFormats.
11. THE Test_Taking_UI SHALL be mobile-first and responsive, using Tailwind CSS breakpoints consistent with the existing Soul Reel frontend.
12. THE Test_Taking_UI SHALL integrate with the existing VideoRecorder component for video prompt recording.
13. THE Test_Taking_UI SHALL be accessible via the `/personal-insights` route, replacing the current "Coming Soon" placeholder.

### Requirement 11: API Gateway Integration

**User Story:** As a developer, I want the psychological testing API endpoints integrated with the existing API Gateway, so that they are secured by Cognito authentication and follow the project's CORS configuration.

#### Acceptance Criteria

1. THE SAM template SHALL define the following API endpoints secured by CognitoAuthorizer: POST /psych-tests/score, GET /psych-tests/list, GET /psych-tests/{testId}, POST /psych-tests/progress/save, GET /psych-tests/progress/{testId}, and POST /psych-tests/export.
2. WHEN any psych-test API endpoint returns a response, THE response SHALL include the header `Access-Control-Allow-Origin` set to `os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')`.
3. THE SAM template SHALL define the ALLOWED_ORIGIN environment variable for all psych-test Lambda functions via the existing Globals.Function.Environment.Variables block.
4. THE SAM template SHALL define environment variables for the new DynamoDB table names (TABLE_PSYCH_TESTS, TABLE_USER_TEST_PROGRESS, TABLE_USER_TEST_RESULTS) in the Globals block.

### Requirement 12: Three Initial Test Definitions

**User Story:** As a legacy maker, I want the IPIP-NEO-60, OEJTS, and Personality-Based Emotional Intelligence tests available at launch, so that I can begin building my Legacy Portrait immediately.

#### Acceptance Criteria

1. THE system SHALL include a Test_Definition JSON file for the IPIP-NEO-60 test with 60 questions measuring the Big Five personality domains (Openness, Conscientiousness, Extraversion, Agreeableness, Neuroticism) and their facets.
2. THE system SHALL include a Test_Definition JSON file for the Open Extended Jungian Type Scales (OEJTS) test with 60 items producing a 16-type personality classification.
3. THE system SHALL include a Test_Definition JSON file for the Personality-Based Emotional Intelligence Test from Open Source Psychometrics.
4. WHEN all three tests are scored for a user, THE ScorePsychTest_Lambda SHALL apply compositeRules to generate a unified Legacy_Portrait combining Big Five traits, Jungian type, and emotional intelligence scores.
5. THE three Test_Definition JSON files SHALL be stored in the repository at `SamLambda/psych-tests/` and deployed to S3 during the SAM deployment process.
