# Requirements Document

## Introduction

This feature makes AI conversation responses theme-aware by composing the final system prompt from three parts: the base system prompt (already editable in Admin > System Settings), the current theme name, and a per-theme prompt description. Theme descriptions are editable by admins in the existing Theme Settings page. At conversation time, the WebSocket Lambda fetches theme metadata from allQuestionDB during `handle_start_conversation`, composes the final prompt using safe string formatting (escaping user-provided values and using a `SafeDict` to preserve the `{question}` placeholder), stores it in ConversationState for reuse across turns, and passes it through to `generate_ai_response` in llm.py — which currently performs the `system_prompt.format(question=question_text)` call on line 45. Both the text-based (`handle_user_response`) and audio-based (`handle_audio_response`) conversation paths must use the composed prompt.

## Glossary

- **Base_System_Prompt**: The existing conversation system prompt stored in SSM at `/virtuallegacy/conversation/system-prompt` and editable via Admin > System Settings. Contains the `{question}` placeholder and will be extended with `{theme_name}` and `{theme_description}` placeholders.
- **Theme_Description**: A free-text field (a few sentences) of additional context specific to a theme (e.g., "Focus on early childhood experiences, family dynamics, and formative memories"). Stored as a new attribute `promptDescription` on question records in allQuestionDB.
- **Theme_Name**: The human-friendly name for a question group (e.g., "Childhood Memories", "School Days and Education"). Already stored as `themeName` in allQuestionDB.
- **Question_Type**: The machine key for a theme (e.g., `childhoodmemories`). Already stored as `questionType` in allQuestionDB and used as the sort key. Derived from a questionId by splitting on the last hyphen and taking the prefix (e.g., `childhoodmemories-3` → `childhoodmemories`).
- **Composed_Prompt**: The final system prompt template sent to Bedrock, formed by inserting Theme_Name and Theme_Description into the Base_System_Prompt's `{theme_name}` and `{theme_description}` placeholders. The `{question}` placeholder remains unsubstituted at this stage — it is resolved later by `generate_ai_response` in llm.py.
- **Admin_Theme_Settings_Page**: The existing frontend page (`ThemeSettings.tsx`) where admins manage per-theme settings such as life event tags and instanceable configuration.
- **WebSocket_Lambda**: The `WebSocketDefaultFunction` Lambda (`wsDefault/app.py`) that handles real-time conversations via WebSocket, including loading config from SSM and routing to `handle_start_conversation`, `handle_user_response`, and `handle_audio_response`.
- **LLM_Module**: The `llm.py` module within the WebSocket Lambda that calls Bedrock. Its `generate_ai_response` function receives a `system_prompt` parameter and calls `system_prompt.format(question=question_text)` to produce the final prompt sent to Bedrock.
- **AdminThemes_Lambda**: The `AdminThemesFunction` Lambda that applies theme-level settings to all questions sharing a `questionType`. Currently uses a DynamoDB Scan with FilterExpression to find matching questions, then updates each with `update_item`.
- **allQuestionDB**: The DynamoDB table storing all questions, keyed by `questionId` (partition key) and `questionType` (sort key).
- **ConversationState**: The class in `conversation_state.py` that tracks conversation progress. State is serialized via `to_dict()`, persisted to DynamoDB (ConversationStateDB) between Lambda invocations, and reconstructed via `from_dict()`.

## Requirements

### Requirement 1: Store Theme Description per Theme

**User Story:** As an admin, I want to add a prompt description to each theme, so that the AI receives theme-specific context during conversations.

#### Acceptance Criteria

1. THE AdminThemes_Lambda SHALL accept an optional `promptDescription` field (string, max 1000 characters) in the PUT request body alongside existing fields (`requiredLifeEvents`, `isInstanceable`, `instancePlaceholder`).
2. WHEN an admin submits a theme update with a `promptDescription` key present in the request body, THE AdminThemes_Lambda SHALL include `promptDescription` in the `UpdateExpression` SET clause for every question record matching the given Question_Type in allQuestionDB.
3. WHEN an admin submits a theme update without a `promptDescription` key in the request body, THE AdminThemes_Lambda SHALL omit `promptDescription` from the `UpdateExpression`, leaving the existing attribute unchanged on question records.
4. WHEN a `promptDescription` value exceeds 1000 characters, THE AdminThemes_Lambda SHALL return a 400 status code with a descriptive error message before performing any DynamoDB writes.
5. THE AdminThemes_Lambda SHALL accept an empty string as a valid `promptDescription` value, clearing the theme description for that theme.

### Requirement 2: Admin UI for Editing Theme Descriptions

**User Story:** As an admin, I want to edit theme prompt descriptions in the Theme Settings page, so that I can tailor AI behavior per theme without leaving the familiar admin interface.

#### Acceptance Criteria

1. THE Admin_Theme_Settings_Page SHALL display a "Prompt Description" text area for each theme when the theme is in edit mode.
2. THE Admin_Theme_Settings_Page SHALL load and display the current `promptDescription` value from the question data for each theme.
3. WHEN an admin modifies the prompt description and clicks Apply, THE Admin_Theme_Settings_Page SHALL include the `promptDescription` field in the PUT request to the AdminThemes_Lambda.
4. THE Admin_Theme_Settings_Page SHALL display a character counter showing current length out of 1000 maximum characters for the prompt description text area.
5. IF the prompt description exceeds 1000 characters, THEN THE Admin_Theme_Settings_Page SHALL disable the Apply button and display a validation message.
6. THE Admin_Theme_Settings_Page SHALL display placeholder text in the prompt description text area that guides the admin (e.g., "Describe the theme context for the AI interviewer...").
7. THE QuestionRecord interface in `adminService.ts` SHALL include a `promptDescription` field of type string.
8. THE ThemeInfo interface in `ThemeSettings.tsx` SHALL include a `currentPromptDescription` field, populated from the first question record of each theme group.
9. THE `applyThemeDefaults` function in `adminService.ts` SHALL accept `promptDescription` as an optional field in its settings parameter and include it in the PUT request body when present.
10. THE Admin_Theme_Settings_Page SHALL display the current prompt description in the non-edit summary line for each theme card (below the existing tags display), showing a truncated preview or "No prompt description" when empty.

### Requirement 3: Fetch Theme Context at Conversation Start

**User Story:** As a developer, I want the conversation flow to include theme metadata, so that the WebSocket Lambda can compose a theme-aware prompt.

#### Acceptance Criteria

1. WHEN a conversation starts with a `questionId`, THE WebSocket_Lambda SHALL derive the Question_Type by calling `question_id.rsplit('-', 1)[0]` to remove the trailing numeric suffix.
2. WHEN a conversation starts, THE WebSocket_Lambda SHALL call `dynamodb.Table(table_name).get_item(Key={'questionId': question_id, 'questionType': question_type})` using both the partition key (`questionId`) and the derived sort key (`questionType`) to retrieve the `themeName` and `promptDescription` attributes from allQuestionDB.
3. IF the allQuestionDB GetItem returns no `promptDescription` attribute or the attribute is empty, THEN THE WebSocket_Lambda SHALL use an empty string as the Theme_Description.
4. IF the allQuestionDB GetItem returns no `themeName` attribute, THEN THE WebSocket_Lambda SHALL use an empty string as the Theme_Name.
5. IF the allQuestionDB GetItem call fails, THEN THE WebSocket_Lambda SHALL log the error and fall back to using empty strings for both Theme_Name and Theme_Description, allowing the conversation to proceed with the base prompt only.

### Requirement 4: Compose Theme-Aware System Prompt

**User Story:** As a user, I want the AI interviewer to understand the current conversation theme, so that follow-up questions are more relevant and contextually appropriate.

#### Acceptance Criteria

1. THE WebSocket_Lambda SHALL compose the Composed_Prompt using a two-step safe substitution: first, escape any literal curly braces in `theme_name` and `theme_description` by replacing `{` with `{{` and `}` with `}}`; then call `system_prompt.format(theme_name=escaped_theme_name, theme_description=escaped_theme_description)` on the Base_System_Prompt. This substitutes only the `{theme_name}` and `{theme_description}` placeholders while leaving the `{question}` placeholder intact (since no `question` kwarg is provided, Python's `str.format` will leave `{question}` unresolved only if we use `format_map` — see clarification below). **Implementation detail**: use `system_prompt.format_map(SafeDict(theme_name=escaped_theme_name, theme_description=escaped_theme_description))` where `SafeDict` is a dict subclass whose `__missing__` method returns `'{' + key + '}'`, preserving unrecognized placeholders (including `{question}`) as literal text in the output.
2. THE Composed_Prompt SHALL preserve the `{question}` placeholder unsubstituted, because `generate_ai_response` in the LLM_Module calls `system_prompt.format(question=question_text)` to resolve it at call time. The `SafeDict.__missing__` method ensures `{question}` passes through as `{question}` in the Composed_Prompt.
3. WHEN both Theme_Name and Theme_Description are empty strings, THE Composed_Prompt SHALL contain the base prompt with empty values substituted for the theme placeholders, preserving backward compatibility.
4. THE Composed_Prompt SHALL be stored in ConversationState as a new `composed_prompt` field, serialized via `to_dict()` and deserialized via `from_dict()`, so that it persists across Lambda invocations within the same conversation session.
5. THE `handle_user_response` function SHALL pass `state.composed_prompt` (instead of `config['system_prompt']`) to `process_user_response_parallel` as the `system_prompt` parameter.
6. THE `handle_audio_response` function SHALL pass `state.composed_prompt` (instead of `config['system_prompt']`) to `process_user_response_parallel` as the `system_prompt` parameter.
7. THE LLM_Module `generate_ai_response` function SHALL continue to call `system_prompt.format(question=question_text)` to resolve the `{question}` placeholder — no changes to llm.py are required for theme composition.
8. IF the admin-authored Theme_Description contains literal curly braces (e.g., "Focus on {family} dynamics"), THEN THE escaping step (replacing `{` with `{{` and `}` with `}}` in the theme values before formatting) SHALL prevent a KeyError or unintended substitution by ensuring those braces are treated as literal text in the output.

### Requirement 5: Update Base System Prompt Template

**User Story:** As an admin, I want the base system prompt to include theme placeholders, so that theme context is injected into the AI's instructions.

#### Acceptance Criteria

1. THE Base_System_Prompt stored in SSM SHALL be updated to include `{theme_name}` and `{theme_description}` placeholders at the appropriate location within the prompt text.
2. WHEN an admin edits the Base_System_Prompt via System Settings, THE Admin_Settings_Page SHALL allow the admin to position the `{theme_name}` and `{theme_description}` placeholders anywhere within the prompt text.
3. THE System Settings description for the Conversation System Prompt setting SHALL document the available placeholders: `{question}`, `{theme_name}`, and `{theme_description}`.

### Requirement 6: IAM Permissions and Environment Variables for DynamoDB Access

**User Story:** As a developer, I want the WebSocket Lambda to have permission to read from allQuestionDB, so that theme lookups do not fail with access errors.

#### Acceptance Criteria

1. THE WebSocket_Lambda IAM policy in `template.yml` SHALL include a Statement granting `dynamodb:GetItem` permission on the allQuestionDB table ARN (`arn:aws:dynamodb:${AWS::Region}:${AWS::AccountId}:table/allQuestionDB`).
2. THE WebSocket_Lambda environment variables in `template.yml` SHALL include `TABLE_ALL_QUESTIONS` set to `allQuestionDB` (this variable already exists in Globals but must be accessible to the WebSocket Lambda).
3. THE WebSocket_Lambda IAM policy already includes `kms:Decrypt` and `kms:DescribeKey` on the DataEncryptionKey ARN, which covers allQuestionDB since it uses the same KMS key. No additional KMS policy changes are required.

### Requirement 7: ConversationState Persistence for Composed Prompt

**User Story:** As a developer, I want the composed prompt to survive across Lambda invocations within a conversation, so that every turn uses the same theme-aware prompt without re-fetching theme data.

#### Acceptance Criteria

1. THE ConversationState class SHALL include a `composed_prompt` attribute initialized to an empty string in `__init__`.
2. THE `to_dict` method SHALL include `composedPrompt` in the serialized dictionary.
3. THE `from_dict` class method SHALL read `composedPrompt` from the DynamoDB item dictionary and assign it to `state.composed_prompt`, defaulting to an empty string if the key is absent (for backward compatibility with existing conversations).
4. WHEN `composed_prompt` is an empty string at the time `handle_user_response` or `handle_audio_response` is called, THE WebSocket_Lambda SHALL fall back to using `config['system_prompt']` as the system prompt, ensuring existing in-flight conversations are not broken.
