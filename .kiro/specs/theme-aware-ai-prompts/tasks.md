# Implementation Plan: Theme-Aware AI Prompts

## Overview

This plan implements theme-aware AI conversation prompts across four layers: infrastructure (template.yml), backend (ConversationState, WebSocket Lambda, AdminThemes Lambda), frontend (adminService.ts, ThemeSettings.tsx), and tests. Tasks are ordered so that infrastructure changes land first (required for backend), ConversationState changes next (dependency for WebSocket Lambda), then the two independent backend paths (AdminThemes and WebSocket Lambda), and finally frontend changes (which depend on AdminThemes). Tests are written alongside each implementation task.

## Tasks

- [x] 1. Infrastructure — Add DynamoDB permissions and env var for WebSocket Lambda
  - [x] 1.1 Add `TABLE_ALL_QUESTIONS: allQuestionDB` to WebSocketDefaultFunction Environment Variables in `SamLambda/template.yml`
    - Add the env var in the `Environment.Variables` block alongside the existing variables (after `TABLE_SUBSCRIPTIONS`)
    - _Requirements: 6.2_

  - [x] 1.2 Add IAM policy statement granting `dynamodb:GetItem` on allQuestionDB to WebSocketDefaultFunction in `SamLambda/template.yml`
    - Add a new `- Statement:` block with `Effect: Allow`, `Action: dynamodb:GetItem`, `Resource: !Sub arn:aws:dynamodb:${AWS::Region}:${AWS::AccountId}:table/allQuestionDB`
    - Place it after the existing DynamoDB policy statements
    - Note: existing `kms:Decrypt` and `kms:DescribeKey` on DataEncryptionKey already covers allQuestionDB — no additional KMS policy needed
    - _Requirements: 6.1, 6.3_

  - [x] 1.3 Write unit tests to validate template.yml contains the required env var and IAM policy
    - Parse `SamLambda/template.yml` and assert `TABLE_ALL_QUESTIONS` is present in WebSocketDefaultFunction's Environment Variables
    - Assert a policy statement with `dynamodb:GetItem` on `allQuestionDB` exists in WebSocketDefaultFunction's Policies
    - Use pytest; test file: `SamLambda/tests/test_template_theme_permissions.py`
    - _Requirements: 6.1, 6.2_

- [x] 2. Backend — ConversationState persistence for composed prompt
  - [x] 2.1 Add `composed_prompt` attribute to ConversationState in `SamLambda/functions/conversationFunctions/wsDefault/conversation_state.py`
    - Add `self.composed_prompt = ""` in `__init__`
    - Add `'composedPrompt': self.composed_prompt` in `to_dict()`
    - Add `state.composed_prompt = data.get('composedPrompt', '')` in `from_dict()`
    - Default to empty string for backward compatibility with existing conversations
    - _Requirements: 7.1, 7.2, 7.3_

  - [x] 2.2 Write unit tests for ConversationState composed_prompt serialization
    - Test that `to_dict()` includes `composedPrompt` key
    - Test that `from_dict()` restores `composed_prompt` correctly
    - Test that `from_dict()` defaults to `""` when `composedPrompt` key is absent (backward compat)
    - Test round-trip: create state → set composed_prompt → to_dict → from_dict → verify equality
    - Use pytest; test file: `SamLambda/tests/test_conversation_state_composed_prompt.py`
    - _Requirements: 7.1, 7.2, 7.3_

  - [x] 2.3 Write property test for ConversationState composed_prompt round-trip (Property 4)
    - **Property 4: ConversationState composed_prompt Serialization Round-Trip**
    - For any ConversationState with an arbitrary `composed_prompt` string, `to_dict()` → `from_dict()` SHALL produce a state with equal `composed_prompt`
    - For any dict without `composedPrompt` key, `from_dict()` SHALL produce `composed_prompt == ""`
    - Use Hypothesis with `st.text()` generator for composed_prompt values
    - Test file: `SamLambda/tests/test_conversation_state_composed_prompt.py` (append to same file)
    - Note: conftest.py already adds wsDefault to sys.path, so ConversationState imports will resolve
    - **Validates: Requirements 4.4, 7.1, 7.2, 7.3**

- [x] 3. Checkpoint — Verify infrastructure and ConversationState changes
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Backend — WebSocket Lambda theme-aware prompt composition
  - [x] 4.1 Add SafeDict class and modify `handle_start_conversation` in `SamLambda/functions/conversationFunctions/wsDefault/app.py`
    - Add `SafeDict(dict)` class with `__missing__` method returning `'{' + key + '}'`
    - In `handle_start_conversation`, after creating `ConversationState` and before `set_conversation`:
      - Derive `question_type = question_id.rsplit('-', 1)[0]`
      - Fetch theme metadata from allQuestionDB using `_dynamodb.Table(os.environ.get('TABLE_ALL_QUESTIONS', 'allQuestionDB')).get_item(Key={'questionId': question_id, 'questionType': question_type})`
      - Extract `themeName` and `promptDescription` with `.get()` defaulting to `""`
      - Escape theme values: replace `{` with `{{` and `}` with `}}`
      - Compose prompt: `config['system_prompt'].format_map(SafeDict(theme_name=escaped_name, theme_description=escaped_desc))`
      - Store in `state.composed_prompt`
    - Wrap the DynamoDB call in try/except, logging errors and falling back to empty strings
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3, 4.8_

  - [x] 4.2 Modify `handle_user_response` to use composed prompt in `SamLambda/functions/conversationFunctions/wsDefault/app.py`
    - Change the `system_prompt` argument in `process_user_response_parallel` call from `config['system_prompt']` to `state.composed_prompt if state.composed_prompt else config['system_prompt']`
    - _Requirements: 4.5, 7.4_

  - [x] 4.3 Modify `handle_audio_response` to use composed prompt in `SamLambda/functions/conversationFunctions/wsDefault/app.py`
    - Change the `system_prompt` argument in `process_user_response_parallel` call from `config['system_prompt']` to `state.composed_prompt if state.composed_prompt else config['system_prompt']`
    - _Requirements: 4.6, 7.4_

  - [x] 4.4 Write unit tests for WebSocket Lambda theme-aware prompt logic
    - Test `SafeDict.__missing__` returns `'{key}'` for unknown keys
    - Test `handle_start_conversation` fetches theme metadata and composes prompt correctly (mock DynamoDB `get_item`)
    - Test `handle_start_conversation` falls back to empty strings when `get_item` raises an exception
    - Test `handle_start_conversation` handles missing `themeName` and `promptDescription` attributes gracefully
    - Test questionType derivation with hyphens in the type name (e.g., `childhood-memories-3` → `childhood-memories`)
    - Test `handle_user_response` passes `state.composed_prompt` to `process_user_response_parallel` when composed_prompt is non-empty
    - Test `handle_user_response` falls back to `config['system_prompt']` when `state.composed_prompt` is empty
    - Test `handle_audio_response` passes `state.composed_prompt` to `process_user_response_parallel` when composed_prompt is non-empty
    - Test `handle_audio_response` falls back to `config['system_prompt']` when `state.composed_prompt` is empty
    - Test prompt composition with theme values containing literal curly braces (e.g., "Focus on {family} dynamics")
    - Mock DynamoDB, SSM, Bedrock, Polly, S3, and Transcribe calls
    - Use pytest; test file: `SamLambda/tests/test_ws_theme_aware_prompts.py`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.5, 4.6, 4.8, 7.4_

  - [x] 4.5 Write property test for SafeDict prompt composition (Property 3)
    - **Property 3: SafeDict Prompt Composition Preserves {question} and Substitutes Theme Values**
    - For any base prompt containing `{question}`, `{theme_name}`, `{theme_description}` and for any theme_name/theme_description strings (including strings with literal curly braces):
      - `{question}` is preserved as a literal placeholder in the output
      - `{theme_name}` is substituted with the original theme_name value
      - `{theme_description}` is substituted with the original theme_description value
      - No `KeyError` is raised
    - Use Hypothesis with `st.text()` for theme values including `{`, `}`, `{word}` patterns
    - Test file: `SamLambda/tests/test_ws_theme_aware_prompts.py` (append to same file)
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.8**

  - [x] 4.6 Write property test for questionId type derivation (Property 2)
    - **Property 2: questionId Type Derivation**
    - For any valid questionId in format `"{type}-{number}"` (where type may contain hyphens), `questionId.rsplit('-', 1)[0]` SHALL produce the correct questionType prefix
    - Use Hypothesis with `st.from_regex(r'[a-z]+-[0-9]+', fullmatch=True)` plus types with embedded hyphens
    - Test file: `SamLambda/tests/test_ws_theme_aware_prompts.py` (append to same file)
    - **Validates: Requirements 3.1**

- [x] 5. Backend — AdminThemes Lambda dynamic UpdateExpression and validation
  - [x] 5.1 Modify AdminThemes Lambda to accept and validate `promptDescription` in `SamLambda/functions/adminFunctions/adminThemes/app.py`
    - Parse `promptDescription` from request body with `body.get('promptDescription')` (None if absent)
    - Validate: if `promptDescription is not None and len(promptDescription) > 1000`, return 400 with descriptive error
    - Build `UpdateExpression` and `ExpressionAttributeValues` dynamically: always include `requiredLifeEvents`, `isInstanceable`, `instancePlaceholder`, `lastModifiedBy`, `lastModifiedAt`; conditionally append `promptDescription = :pd` only when `promptDescription is not None`
    - Replace the hardcoded `UpdateExpression` string with the dynamic version
    - Empty string is a valid value (clears the description)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [x] 5.2 Update `SamLambda/tests/conftest.py` to add adminThemes function directory to sys.path
    - Add `os.path.join(_SAMLAMBDA_ROOT, 'functions', 'adminFunctions', 'adminThemes')` to `_FUNCTION_DIRS`
    - Also add the shared layer path `os.path.join(_SAMLAMBDA_ROOT, 'functions', 'shared', 'python')` if not already present
    - This is required for AdminThemes tests to resolve imports like `cors`, `responses`, `admin_auth`, `life_event_registry`

  - [x] 5.3 Write unit tests for AdminThemes Lambda promptDescription handling
    - Test that `promptDescription` is included in UpdateExpression when present in request body
    - Test that `promptDescription` is omitted from UpdateExpression when absent from request body
    - Test that empty string `""` is accepted as valid promptDescription
    - Test that promptDescription exceeding 1000 characters returns 400 status code with error message
    - Test that promptDescription of exactly 1000 characters is accepted
    - Test that promptDescription of exactly 1001 characters is rejected
    - Mock DynamoDB scan and update_item calls
    - Use pytest; test file: `SamLambda/tests/test_admin_themes_prompt_description.py`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [x] 5.4 Write property test for promptDescription length validation (Property 1)
    - **Property 1: promptDescription Length Validation**
    - For any string `s`, the validation logic SHALL accept `s` if and only if `len(s) <= 1000`; strings longer than 1000 SHALL be rejected with 400
    - Use Hypothesis with `st.text(min_size=0, max_size=2000)` generator
    - Test file: `SamLambda/tests/test_admin_themes_prompt_description.py` (append to same file)
    - **Validates: Requirements 1.1, 1.4, 1.5**

- [x] 6. Checkpoint — Verify all backend changes and tests
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Frontend — adminService.ts type and function updates
  - [x] 7.1 Update `QuestionRecord` interface and `applyThemeDefaults` function in `FrontEndCode/src/services/adminService.ts`
    - Add `promptDescription?: string` field to the `QuestionRecord` interface
    - Update `applyThemeDefaults` settings parameter type to include `promptDescription?: string`
    - No other changes needed — the function already passes `settings` directly to `JSON.stringify`
    - _Requirements: 2.7, 2.9_

  - [x] 7.2 Write unit tests for adminService.ts changes
    - Test that `QuestionRecord` type accepts objects with `promptDescription` field
    - Test that `applyThemeDefaults` includes `promptDescription` in the request body when provided
    - Test that `applyThemeDefaults` works without `promptDescription` (backward compat)
    - Use vitest; test file: `FrontEndCode/src/__tests__/admin-service-prompt-description.test.ts`
    - _Requirements: 2.7, 2.9_

- [x] 8. Frontend — ThemeSettings.tsx UI for prompt description editing
  - [x] 8.1 Update ThemeInfo interface and state management in `FrontEndCode/src/pages/admin/ThemeSettings.tsx`
    - Add `currentPromptDescription: string` to `ThemeInfo` interface
    - Add `editPromptDescription` state variable (useState)
    - Populate `currentPromptDescription` from `first.promptDescription || ""` in `loadThemes`
    - Set `editPromptDescription` in `startEdit` from `t.currentPromptDescription`
    - Include `promptDescription: editPromptDescription` in the `applyThemeDefaults` call in `handleApply`
    - _Requirements: 2.2, 2.3, 2.8_

  - [x] 8.2 Add prompt description textarea, character counter, and validation to edit mode in `FrontEndCode/src/pages/admin/ThemeSettings.tsx`
    - Add a `<textarea>` with placeholder "Describe the theme context for the AI interviewer..." after the instanceable section and before Apply/Cancel buttons
    - Add character counter showing `{editPromptDescription.length}/1000`
    - When length > 1000: show red validation text and disable the Apply button
    - _Requirements: 2.1, 2.4, 2.5, 2.6_

  - [x] 8.3 Add prompt description summary display in non-edit mode in `FrontEndCode/src/pages/admin/ThemeSettings.tsx`
    - Below the existing tags summary line, show the current prompt description
    - If `currentPromptDescription` is non-empty, show a truncated preview (e.g., first 100 chars + "...")
    - If empty, show "No prompt description"
    - _Requirements: 2.10_

  - [x] 8.4 Write unit tests for ThemeSettings.tsx prompt description UI
    - Test that textarea renders in edit mode with correct placeholder text
    - Test that textarea loads and displays the current `promptDescription` value
    - Test that character counter displays correct count (e.g., "50/1000")
    - Test that Apply button is disabled when promptDescription exceeds 1000 characters
    - Test that validation message appears when exceeding 1000 characters
    - Test that Apply includes `promptDescription` in the request payload
    - Test that non-edit summary shows truncated description when present
    - Test that non-edit summary shows "No prompt description" when empty
    - Use vitest with React Testing Library; test file: `FrontEndCode/src/__tests__/theme-settings-prompt-description.test.tsx`
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.10_

- [x] 9. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Update System Settings description for Conversation System Prompt
  - [x] 10.1 Update the `description` field of the `CONVERSATION_SYSTEM_PROMPT` record in SystemSettingsDB to document available placeholders
    - The description should mention the three available placeholders: `{question}`, `{theme_name}`, and `{theme_description}`
    - This can be done via the Admin Settings API or directly in DynamoDB
    - _Requirements: 5.3_

## Notes

- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- No changes to `llm.py`, `config.py`, or `adminSettings/app.py` are required
- Requirement 5 ACs 5.1 and 5.2 (updating the base system prompt SSM value and allowing admin positioning of placeholders) are manual admin actions via System Settings — not coding tasks. AC 5.3 (documenting placeholders in the setting description) is covered by Task 10
