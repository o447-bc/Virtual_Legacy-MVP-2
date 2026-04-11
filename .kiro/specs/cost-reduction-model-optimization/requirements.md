# Requirements Document

## Introduction

This feature switches two backend LLM workloads — depth scoring and transcript summarization — from Claude 3 Haiku to Amazon Nova Micro on AWS Bedrock. The goal is to reduce per-invocation costs by 70-89% on these two tasks while preserving output quality. The conversation response generation model (Claude 3.5 Sonnet v2) remains unchanged.

## Glossary

- **Scoring_Function**: The `score_response_depth()` function in `wsDefault/llm.py` that evaluates the depth of a user's conversational response and returns a numeric score plus reasoning.
- **Summarization_Function**: The `invoke_bedrock()` and `parse_bedrock_response()` functions in `summarizeTranscript/app.py` that generate a JSON summary of a user's video/audio transcript.
- **Nova_Micro**: The Amazon Nova Micro foundation model (`amazon.nova-micro-v1:0`), a low-cost text model on AWS Bedrock.
- **Haiku**: The Claude 3 Haiku foundation model (`anthropic.claude-3-haiku-20240307-v1:0`), the current model used for scoring and summarization.
- **SSM_Parameter**: An AWS Systems Manager Parameter Store entry used to configure model IDs at runtime without code deploys.
- **IAM_Policy**: The inline AWS IAM policy in `template.yml` that grants a Lambda function permission to invoke specific Bedrock foundation models.
- **Scoring_Prompt**: The SSM parameter at `/virtuallegacy/conversation/scoring-prompt` that instructs the scoring model on expected output format.
- **Summarization_Prompt**: The SSM parameter at `/life-story-app/llm-prompts/combined-prompt` that instructs the summarization model to produce structured JSON output.
- **WebSocketDefaultFunction**: The Lambda function that handles real-time conversation turns, including parallel scoring and response generation.
- **SummarizeTranscriptFunction**: The Lambda function that generates summaries of user video/audio transcripts.
- **Bedrock_Request_Body**: The JSON payload sent to the Bedrock `InvokeModel` API, including model-specific fields like `anthropic_version`, `max_tokens`, and `temperature`.

## Requirements

### Requirement 1: Grant Bedrock IAM Access for Nova Micro on WebSocketDefaultFunction

**User Story:** As a platform operator, I want the WebSocketDefaultFunction to have IAM permission to invoke Amazon Nova Micro, so that the scoring model switch does not cause AccessDeniedException errors.

#### Acceptance Criteria

1. THE IAM_Policy for WebSocketDefaultFunction SHALL include `arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-micro-v1:0` in the `bedrock:InvokeModel` resource list.
2. THE IAM_Policy for WebSocketDefaultFunction SHALL retain all existing Bedrock model ARNs (Sonnet v2, Sonnet v1, Haiku, Haiku inference profile) alongside the new Nova Micro ARN.
3. WHEN the updated template is deployed, THE WebSocketDefaultFunction SHALL invoke Nova Micro without receiving an AccessDeniedException.

### Requirement 2: Grant Bedrock IAM Access for Nova Micro on SummarizeTranscriptFunction

**User Story:** As a platform operator, I want the SummarizeTranscriptFunction to have IAM permission to invoke Amazon Nova Micro, so that the summarization model switch does not cause AccessDeniedException errors.

#### Acceptance Criteria

1. THE IAM_Policy for SummarizeTranscriptFunction SHALL include `arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-micro-v1:0` in the `bedrock:InvokeModel` resource list.
2. THE IAM_Policy for SummarizeTranscriptFunction SHALL retain the existing Haiku and Sonnet ARNs alongside the new Nova Micro ARN.
3. WHEN the updated template is deployed, THE SummarizeTranscriptFunction SHALL invoke Nova Micro without receiving an AccessDeniedException.

### Requirement 3: Adapt Scoring Request Body for Nova Micro Compatibility

**User Story:** As a platform operator, I want the depth scoring function to construct a Bedrock request body compatible with Amazon Nova Micro, so that scoring calls succeed after the model switch.

#### Acceptance Criteria

1. WHEN the configured scoring model ID starts with `amazon.nova`, THE Scoring_Function SHALL construct a Bedrock_Request_Body using the Nova-native `inferenceConfig` format (with `maxTokens` and `temperature` fields) instead of the Anthropic Messages API format.
2. WHEN the configured scoring model ID starts with `anthropic.`, THE Scoring_Function SHALL continue to construct a Bedrock_Request_Body using the Anthropic Messages API format (`anthropic_version`, `max_tokens`, `temperature`, `messages`).
3. THE Scoring_Function SHALL extract the text content from a Nova Micro response body using the `output.message.content[0].text` path.
4. THE Scoring_Function SHALL extract the text content from an Anthropic response body using the `content[0].text` path.

### Requirement 4: Adapt Summarization Request Body for Nova Micro Compatibility

**User Story:** As a platform operator, I want the summarization function to construct a Bedrock request body compatible with Amazon Nova Micro, so that summarization calls succeed after the model switch.

#### Acceptance Criteria

1. WHEN the configured summarization model ID starts with `amazon.nova`, THE Summarization_Function SHALL construct a Bedrock_Request_Body using the Nova-native `inferenceConfig` format (with `maxTokens` and `temperature` fields) instead of the Anthropic Messages API format.
2. WHEN the configured summarization model ID starts with `anthropic.`, THE Summarization_Function SHALL continue to construct a Bedrock_Request_Body using the Anthropic Messages API format.
3. THE Summarization_Function SHALL extract the text content from a Nova Micro response body using the `output.message.content[0].text` path.
4. THE Summarization_Function SHALL extract the text content from an Anthropic response body using the `content[0].text` path.

### Requirement 5: Preserve Scoring Output Parsing

**User Story:** As a platform operator, I want the scoring function to correctly parse Nova Micro's output into a numeric score and reasoning, so that conversation depth tracking continues to work.

#### Acceptance Criteria

1. WHEN Nova Micro returns a bare numeric value, THE Scoring_Function SHALL parse the value as a float score and return default reasoning.
2. WHEN Nova Micro returns text in the format "Score: X\nReasoning: ...", THE Scoring_Function SHALL parse the score and reasoning from the structured format.
3. IF the Scoring_Function cannot parse a valid score from the Nova Micro response, THEN THE Scoring_Function SHALL return a fallback score of 1.0 and log the parsing failure.
4. THE Scoring_Function SHALL return scores in the same numeric range (0-3) regardless of which backing model is configured.

### Requirement 6: Preserve Summarization JSON Output Parsing

**User Story:** As a platform operator, I want the summarization function to correctly parse Nova Micro's output into the expected JSON structure, so that transcript summaries continue to populate in the database.

#### Acceptance Criteria

1. WHEN Nova Micro returns a response containing a JSON object, THE Summarization_Function SHALL extract and parse the JSON object from the response text.
2. THE Summarization_Function SHALL validate that the parsed JSON contains the required fields: `oneSentence`, `detailedSummary`, and `thoughtfulnessScore`.
3. THE Summarization_Function SHALL validate that `thoughtfulnessScore` is an integer between 0 and 5 inclusive.
4. IF the Nova Micro response does not contain valid JSON with the required fields, THEN THE Summarization_Function SHALL raise a ValueError with a descriptive message and update the summarization status to FAILED.

### Requirement 7: Update Default Scoring Model in Config

**User Story:** As a platform operator, I want the default scoring model in the application config to reference Nova Micro, so that new deployments use the cost-optimized model without requiring a separate SSM parameter update.

#### Acceptance Criteria

1. THE config module SHALL use `amazon.nova-micro-v1:0` as the default value for the `llm_scoring_model` configuration key when the SSM parameter `/virtuallegacy/conversation/llm-scoring-model` is not set.
2. THE config module SHALL continue to prefer the SSM parameter value over the default when the SSM parameter is set.

### Requirement 8: IAM and Code Changes Deploy Together

**User Story:** As a platform operator, I want the IAM policy additions and the code changes to be deployed in a single SAM deployment, so that there is no window where code references a model the IAM policy does not permit.

#### Acceptance Criteria

1. THE template.yml IAM policy changes (Requirements 1 and 2) and the code changes (Requirements 3 and 4) SHALL be committed and deployed in the same `sam build && sam deploy` operation.
2. WHEN the deployment completes, THE WebSocketDefaultFunction and SummarizeTranscriptFunction SHALL have both the updated code and the updated IAM permissions active simultaneously.
