# Requirements Document

## Introduction

SoulReel currently manages questions in the `allQuestionDB` DynamoDB table via an Excel spreadsheet that is manually migrated to DynamoDB. This workflow is error-prone, lacks validation, and cannot enforce the new life-event metadata attributes (`requiredLifeEvents`, `isInstanceable`, `instancePlaceholder`) required by the upcoming life-events survey feature.

This feature replaces the Excel workflow with a dedicated admin web application hosted under the `/admin` route of the existing Amplify app. The admin tool provides CRUD operations on questions, life-event tagging with validation against a canonical registry, batch import of AI-generated questions, a question assignment simulator, and an audit trail. Access is restricted to users in a `SoulReelAdmins` Cognito group.

## Glossary

- **Admin_Tool**: The React-based admin web application hosted at the `/admin` route of the existing SoulReel Amplify app, accessible only to authenticated users in the `SoulReelAdmins` Cognito group.
- **Admin_API**: The set of Lambda functions behind the existing API Gateway that handle admin CRUD operations on `allQuestionDB`, gated by Cognito authorization and server-side admin group membership verification.
- **Admin_Gate**: The frontend routing logic that checks the authenticated user's Cognito group membership and restricts access to `/admin/*` routes to members of the `SoulReelAdmins` Cognito group.
- **allQuestionDB**: The existing DynamoDB table containing all questions with attributes `questionId` (partition key, string), `questionType` (string), `Difficulty` (number, 1–10), `Valid` (number, 1 or 0), and `Question` (string). New attributes added by this feature: `requiredLifeEvents`, `isInstanceable`, `instancePlaceholder`, `lastModifiedBy`, `lastModifiedAt`.
- **Life_Event_Key**: A unique string identifier for each life event (e.g., `got_married`, `death_of_child`, `first_job`). Includes status-derived keys: `spouse_divorced`, `spouse_deceased`, `spouse_still_married`. Defined in the Canonical_Life_Event_Registry.
- **Canonical_Life_Event_Registry**: A single source-of-truth constant defining all valid Life_Event_Keys, exported as a shared module consumed by both the Admin_Tool frontend (for dropdowns/autocomplete) and backend Lambdas (for validation).
- **Question_Record**: A single item in `allQuestionDB` representing one question with all its attributes.
- **Batch_Import**: The process of pasting multiple questions (plain text or JSON array) into the Admin_Tool, previewing them in a table, and writing them to `allQuestionDB` in a single operation.
- **Assignment_Simulator**: A read-only feature in the Admin_Tool that accepts a set of selected Life_Event_Keys and displays the filtered list of questions that would be assigned to a user with those selections, using the same filtering logic as the Question_Assignment_Service.
- **SoulReelAdmins**: A Cognito user pool group whose members are authorized to access the Admin_Tool and Admin_API endpoints.
- **Soft_Delete**: Setting a question's `Valid` attribute to `0` rather than removing the record from `allQuestionDB`, preserving referential integrity with existing video responses.
- **Coverage_Report**: A dashboard view in the Admin_Tool that lists every Life_Event_Key from the Canonical_Life_Event_Registry alongside the count of valid questions tagged with that key, highlighting keys with zero coverage.
- **Theme**: A grouping of questions identified by their shared `questionType` value (e.g., "Divorce", "Career"). In the original Excel workflow, each tab represented a theme. Theme-level settings allow bulk tagging of all questions within a `questionType`.
- **Theme_Defaults**: The set of life event tags (`requiredLifeEvents`), `isInstanceable` flag, and `instancePlaceholder` value configured at the theme (`questionType`) level, applied as defaults to all questions in that theme.

## Requirements

### Requirement 1: Canonical Life Event Key Registry

**User Story:** As a system architect, I want a single source of truth for all valid Life_Event_Keys, so that the admin tool, survey Lambda, and assignment Lambda all validate against the same set of keys.

#### Acceptance Criteria

1. THE Canonical_Life_Event_Registry SHALL define the following Life_Event_Keys organized by category:
   - Core Relationship & Family: `got_married`, `had_children`, `became_grandparent`, `death_of_child`, `death_of_parent`, `death_of_sibling`, `death_of_friend_mentor`, `estranged_family_member`, `infertility_or_pregnancy_loss`, `raised_child_special_needs`, `falling_out_close_friend`
   - Education & Early Life: `graduated_high_school`, `graduated_college`, `graduate_degree`, `studied_abroad`, `influential_mentor`
   - Career & Professional: `first_job`, `career_change`, `started_business`, `got_fired`, `retired`, `became_mentor`
   - Health & Resilience: `serious_illness`, `mental_health_challenge`, `caregiver`, `addiction_recovery`, `financial_hardship`, `major_legal_issue`
   - Relocation & Transitions: `moved_city`, `immigrated`, `lived_abroad`, `learned_second_language`
   - Spiritual, Creative & Legacy: `spiritual_awakening`, `changed_religion`, `creative_work`, `major_award`, `experienced_discrimination`
   - Other: `military_service`, `survived_disaster`, `near_death`, `act_of_kindness`
   - Status-derived (virtual): `spouse_divorced`, `spouse_deceased`, `spouse_still_married`
2. THE Canonical_Life_Event_Registry SHALL be implemented as a shared TypeScript constant file importable by the Admin_Tool frontend and as a Python constant importable by backend Lambda functions.
3. THE Canonical_Life_Event_Registry SHALL define which Life_Event_Keys are instanceable: `got_married`, `had_children`, `death_of_child`, `death_of_parent`, `death_of_sibling`, `death_of_friend_mentor`.
4. THE Canonical_Life_Event_Registry SHALL define the valid instance placeholders: `{spouse_name}`, `{child_name}`, `{deceased_name}`.
5. THE Canonical_Life_Event_Registry SHALL map each instanceable Life_Event_Key to its corresponding placeholder: `got_married` to `{spouse_name}`, `had_children` to `{child_name}`, and `death_of_child`, `death_of_parent`, `death_of_sibling`, `death_of_friend_mentor` to `{deceased_name}`.

### Requirement 2: Admin Access Control

**User Story:** As a product owner, I want the admin tool to be accessible only to authorized administrators, so that regular legacy makers and benefactors cannot modify question data.

#### Acceptance Criteria

1. THE Admin_Gate SHALL check the authenticated user's Cognito JWT token for membership in the `SoulReelAdmins` group before rendering any `/admin/*` route.
2. WHEN an authenticated user who is not a member of the `SoulReelAdmins` group navigates to any `/admin/*` route, THE Admin_Gate SHALL redirect the user to the Dashboard and display an "Access denied" toast notification.
3. WHEN an unauthenticated user navigates to any `/admin/*` route, THE Admin_Gate SHALL redirect the user to the Login page.
4. THE Admin_API Lambda functions SHALL verify the caller's Cognito group membership by inspecting the `cognito:groups` claim in the decoded JWT token from the `requestContext.authorizer.claims` object.
5. WHEN an Admin_API Lambda receives a request from a user not in the `SoulReelAdmins` group, THE Admin_API Lambda SHALL return HTTP 403 with a JSON body containing `{ "error": "Forbidden: admin access required" }`.
6. THE Admin_API Lambda functions SHALL use the existing CognitoAuthorizer on the API Gateway for JWT validation, and perform the group membership check as an additional server-side authorization step.

### Requirement 3: Question Browsing and Filtering

**User Story:** As an admin, I want to browse and filter all questions in the question bank, so that I can find specific questions to review or edit.

#### Acceptance Criteria

1. THE Admin_Tool SHALL display a paginated table of all Question_Records from allQuestionDB, showing columns for `questionId`, `questionType`, `Difficulty`, `Valid` status, `Question` text (truncated), and life event tag count.
2. THE Admin_Tool SHALL provide a text search input that filters questions by matching against the `Question` text field (case-insensitive substring match).
3. THE Admin_Tool SHALL provide dropdown filters for `questionType` (populated from distinct values in allQuestionDB) and `Difficulty` level (1–10).
4. THE Admin_Tool SHALL provide toggle filters for: valid questions only, invalid questions only, questions with life event tags, questions without life event tags, and instanceable questions only.
5. THE Admin_Tool SHALL support sorting the question table by `questionType`, `Difficulty`, `Valid` status, and `lastModifiedAt`.
6. THE Admin_Tool SHALL display the total count of questions matching the current filter criteria.
7. THE Admin_API SHALL expose a GET endpoint at `/admin/questions` that returns paginated Question_Records from allQuestionDB, accepting query parameters for page size, pagination token, and filter criteria.
8. THE Admin_API GET `/admin/questions` endpoint SHALL require CognitoAuthorizer and server-side admin group verification.

### Requirement 4: Question Detail View and Inline Editing

**User Story:** As an admin, I want to view and edit all attributes of a single question, so that I can update question text, difficulty, validity, and life event tags.

#### Acceptance Criteria

1. WHEN an admin clicks a question row in the browse table, THE Admin_Tool SHALL display a detail/edit panel showing all Question_Record attributes: `questionId` (read-only), `questionType`, `Difficulty`, `Valid`, `Question` text, `requiredLifeEvents`, `isInstanceable`, `instancePlaceholder`, `lastModifiedBy` (read-only), and `lastModifiedAt` (read-only).
2. THE Admin_Tool SHALL allow inline editing of `questionType`, `Difficulty` (number input, 1–10), `Valid` (toggle), and `Question` text (textarea).
3. THE Admin_Tool SHALL provide a life event tag editor for `requiredLifeEvents` that uses a multi-select dropdown populated from the Canonical_Life_Event_Registry, preventing free-text entry of arbitrary keys.
4. THE Admin_Tool SHALL provide a toggle for `isInstanceable` and a dropdown for `instancePlaceholder` populated with the valid placeholders from the Canonical_Life_Event_Registry (`{spouse_name}`, `{child_name}`, `{deceased_name}`).
5. WHEN `isInstanceable` is toggled to `true`, THE Admin_Tool SHALL require the admin to select an `instancePlaceholder` value before saving.
6. WHEN the admin saves changes, THE Admin_Tool SHALL display a confirmation dialog showing the changed fields before submitting.
7. THE Admin_API SHALL expose a PUT endpoint at `/admin/questions/{questionId}` that updates the specified Question_Record in allQuestionDB.
8. WHEN a question is updated via the PUT endpoint, THE Admin_API SHALL set `lastModifiedBy` to the admin user's email (from the JWT `email` claim) and `lastModifiedAt` to the current UTC timestamp in ISO 8601 format.
9. THE Admin_API PUT endpoint SHALL require CognitoAuthorizer and server-side admin group verification.
10. IF the PUT request body contains a `requiredLifeEvents` value that includes a string not present in the Canonical_Life_Event_Registry, THEN THE Admin_API SHALL return HTTP 400 with a descriptive error message identifying the invalid key.

### Requirement 5: Question Validation Warnings

**User Story:** As an admin, I want the tool to warn me about common tagging mistakes, so that I can fix issues before they affect users.

#### Acceptance Criteria

1. WHEN `isInstanceable` is `true` and the `Question` text does not contain the selected `instancePlaceholder` token, THE Admin_Tool SHALL display a warning message: "This question is marked as instanceable but the question text does not contain the placeholder token `{placeholder}`."
2. WHEN `requiredLifeEvents` contains a Life_Event_Key that is not in the Canonical_Life_Event_Registry, THE Admin_Tool SHALL display a warning message identifying the unrecognized key.
3. WHEN `isInstanceable` is `true` and `requiredLifeEvents` does not contain the corresponding instanceable Life_Event_Key (per the registry mapping), THE Admin_Tool SHALL display a warning message: "Instanceable questions should include the matching life event key in requiredLifeEvents."
4. WHEN `isInstanceable` is `false` and `instancePlaceholder` is set, THE Admin_Tool SHALL display a warning message: "This question has a placeholder set but is not marked as instanceable."
5. THE Admin_Tool SHALL display validation warnings inline next to the relevant field, using a yellow/amber visual indicator, and SHALL allow the admin to save despite warnings (warnings are advisory, not blocking).
6. WHEN the admin saves a question (create or edit), THE Admin_Tool SHALL check for exact duplicate `Question` text across all existing Question_Records and display a warning if a duplicate is found, showing the matching questionId(s).
7. WHEN the admin enters a `questionType` value that differs from an existing `questionType` only in casing (e.g., "Divorce" vs "divorce"), THE Admin_Tool SHALL display a warning: "A similar question type '{existingType}' already exists. Question types are case-sensitive — please verify this is intentional."

### Requirement 6: Question Creation

**User Story:** As an admin, I want to create new individual questions, so that I can expand the question bank without using the Excel spreadsheet.

#### Acceptance Criteria

1. THE Admin_Tool SHALL provide a "Create Question" form with input fields for `questionType` (dropdown of existing types or free text for new types), `Difficulty` (number input, 1–10), `Question` text (textarea, required), `requiredLifeEvents` (multi-select from registry), `isInstanceable` (toggle), and `instancePlaceholder` (dropdown, conditional on `isInstanceable`).
2. WHEN the admin submits the create form, THE Admin_API SHALL auto-generate a `questionId` using the format `{questionType}-{sequentialNumber}` where `{questionType}` is the lowercase, hyphenated version of the question type and `{sequentialNumber}` is a zero-padded 5-digit number (e.g., `divorce-00001`, `marriage-00023`). The sequential number SHALL be determined by finding the highest existing number for that questionType prefix in allQuestionDB and incrementing by 1.
3. THE Admin_API SHALL expose a POST endpoint at `/admin/questions` that creates a new Question_Record in allQuestionDB.
4. WHEN a question is created, THE Admin_API SHALL set `Valid` to `1`, `lastModifiedBy` to the admin user's email, and `lastModifiedAt` to the current UTC timestamp.
5. THE Admin_API POST endpoint SHALL require CognitoAuthorizer and server-side admin group verification.
6. IF the create request is missing the required `Question` text or `questionType` field, THEN THE Admin_API SHALL return HTTP 400 with a descriptive error message.
7. THE Admin_API POST endpoint SHALL validate `requiredLifeEvents` values against the Canonical_Life_Event_Registry and return HTTP 400 for invalid keys.

### Requirement 7: Question Soft Delete

**User Story:** As an admin, I want to mark questions as invalid rather than deleting them, so that existing video responses linked to those questions remain intact.

#### Acceptance Criteria

1. THE Admin_Tool SHALL provide a "Mark as Invalid" action on each question that sets the `Valid` attribute to `0`.
2. THE Admin_Tool SHALL provide a "Mark as Valid" action on invalid questions that sets the `Valid` attribute to `1`.
3. WHEN the admin toggles a question's validity, THE Admin_Tool SHALL display a confirmation dialog before submitting the change.
4. THE Admin_Tool SHALL not provide a hard-delete action for questions, preserving referential integrity with video response records in `userQuestionStatusDB`.
5. WHEN a question's `Valid` status is changed, THE Admin_API SHALL update `lastModifiedBy` and `lastModifiedAt` on the Question_Record.

### Requirement 8: Batch Import

**User Story:** As an admin, I want to paste multiple AI-generated questions at once and import them in bulk, so that I can efficiently expand the question bank.

#### Acceptance Criteria

1. THE Admin_Tool SHALL provide a batch import interface with a large textarea for pasting questions and input fields for assigning a shared `questionType` (dropdown or free text) and `Difficulty` level (1–10).
2. THE Admin_Tool SHALL accept two input formats: plain text (one question per line, blank lines ignored) and JSON array (array of strings or array of objects with a `question` field).
3. THE Admin_Tool SHALL provide a multi-select field for assigning shared `requiredLifeEvents` tags to all questions in the batch, populated from the Canonical_Life_Event_Registry.
4. WHEN the admin clicks "Preview", THE Admin_Tool SHALL parse the pasted input and display a preview table showing each parsed question with its auto-generated `questionId`, assigned `questionType`, `Difficulty`, and life event tags.
5. THE Admin_Tool SHALL display the count of parsed questions in the preview and allow the admin to remove individual questions from the batch before importing.
6. WHEN the admin clicks "Import" after preview, THE Admin_API SHALL write all questions to allQuestionDB with auto-generated `questionId` values using the format `{questionType}-{sequentialNumber}` (lowercase, hyphenated question type prefix + zero-padded 5-digit sequential number, e.g., `divorce-00001`). The sequential number SHALL be determined by finding the highest existing number for that questionType prefix in allQuestionDB and incrementing by 1, with sequential numbering continuing across the batch. `Valid` SHALL be set to `1`, `lastModifiedBy` set to the admin's email, and `lastModifiedAt` set to the current UTC timestamp.
7. THE Admin_API SHALL expose a POST endpoint at `/admin/questions/batch` that accepts an array of Question_Records and writes them to allQuestionDB.
8. THE Admin_API batch endpoint SHALL require CognitoAuthorizer and server-side admin group verification.
9. IF any question in the batch fails validation (missing text, invalid life event keys), THEN THE Admin_API SHALL return HTTP 400 with details identifying which questions failed and the reason, without writing any questions from the batch.
10. THE Admin_API batch endpoint SHALL use DynamoDB `BatchWriteItem` for efficient bulk writes, handling the 25-item-per-batch DynamoDB limit internally.
11. WHEN importing questions into a `questionType` that has Theme_Defaults set, THE Admin_Tool SHALL pre-populate the batch import's life event tag fields (`requiredLifeEvents`, `isInstanceable`, `instancePlaceholder`) with the Theme_Defaults. The admin can override these defaults before importing.
12. WHEN batch importing, THE Admin_Tool SHALL check for duplicates both within the batch itself and against existing questions in allQuestionDB, and highlight any duplicates in the preview table.
13. THE batch preview table SHALL highlight questions that have duplicate text (either within the batch or matching existing questions in allQuestionDB) with a yellow/amber warning indicator. The admin can choose to proceed despite duplicates.

### Requirement 9: Assignment Simulator

**User Story:** As an admin, I want to simulate what questions a user with specific life events would see, so that I can verify tagging is correct before it affects real users.

#### Acceptance Criteria

1. THE Admin_Tool SHALL provide a simulator interface with checkboxes for each Life_Event_Key from the Canonical_Life_Event_Registry, organized by category.
2. WHEN the admin selects life events and clicks "Simulate", THE Admin_Tool SHALL display the filtered list of questions that would be assigned to a user with those selections.
3. THE Assignment_Simulator SHALL apply the same filtering logic as the Question_Assignment_Service: include questions with empty `requiredLifeEvents` (universal), include questions where all `requiredLifeEvents` are present in the selected set, and exclude questions where any `requiredLifeEvents` key is absent from the selected set.
4. THE Assignment_Simulator SHALL display results grouped by `questionType`, showing the question count per type and the total assigned question count.
5. THE Assignment_Simulator SHALL visually distinguish instanceable questions in the results and indicate which placeholder would be used.
6. THE Admin_API SHALL expose a POST endpoint at `/admin/simulate` that accepts a list of selected Life_Event_Keys and returns the filtered question list.
7. THE Admin_API simulate endpoint SHALL require CognitoAuthorizer and server-side admin group verification.

### Requirement 10: Audit Trail

**User Story:** As an admin, I want to see who last modified each question and when, so that I can track changes and maintain accountability.

#### Acceptance Criteria

1. THE allQuestionDB table SHALL include `lastModifiedBy` (string, admin email) and `lastModifiedAt` (string, ISO 8601 UTC timestamp) attributes on each Question_Record.
2. WHEN any Admin_API endpoint modifies a Question_Record (create, update, validity toggle, batch import), THE Admin_API SHALL set `lastModifiedBy` to the admin user's email extracted from the JWT `email` claim and `lastModifiedAt` to the current UTC timestamp.
3. THE Admin_Tool question detail view SHALL display `lastModifiedBy` and `lastModifiedAt` as read-only fields.
4. THE Admin_Tool question browse table SHALL support sorting by `lastModifiedAt` to show recently modified questions first.

### Requirement 11: Admin Frontend Routing

**User Story:** As a developer, I want the admin tool hosted under the `/admin` route of the existing app, so that it shares the same deployment and auth infrastructure.

#### Acceptance Criteria

1. THE Admin_Tool SHALL be accessible at the `/admin` route within the existing React/Vite application.
2. THE Admin_Tool SHALL use React Router nested routes under `/admin` for sub-pages: `/admin` (dashboard summary page, default landing page), `/admin/questions` (question browse), `/admin/create` (create question), `/admin/batch` (batch import), `/admin/simulate` (assignment simulator), `/admin/coverage` (life event coverage report), `/admin/themes` (theme-level tagging), and `/admin/export` (export view).
3. THE Admin_Tool SHALL use the existing SoulReel design system: Tailwind CSS, shadcn/ui components, and the project's color tokens (`legacy-purple`, `legacy-navy`).
4. THE Admin_Tool SHALL include a navigation sidebar or tab bar for switching between dashboard, question browse, create, batch import, simulator, coverage report, theme settings, and export views.
5. THE Admin_Tool SHALL display the authenticated admin user's email in the header area.
6. WHEN a non-admin user's browser navigates directly to an `/admin/*` URL, THE Admin_Gate SHALL redirect to the appropriate non-admin page (Dashboard for legacy makers, Benefactor Dashboard for benefactors) with an "Access denied" toast.

### Requirement 12: Admin API Endpoints and SAM Configuration

**User Story:** As a DevOps engineer, I want the admin Lambda functions defined in the SAM template with correct IAM permissions, so that deployment is automated and secure.

#### Acceptance Criteria

1. THE SAM template SHALL define an Admin Questions Lambda function handling GET `/admin/questions`, POST `/admin/questions`, PUT `/admin/questions/{questionId}`, and POST `/admin/questions/batch` with IAM policies granting `dynamodb:Scan`, `dynamodb:Query`, `dynamodb:PutItem`, `dynamodb:UpdateItem`, and `dynamodb:GetItem` on allQuestionDB, and `dynamodb:BatchWriteItem` on allQuestionDB for the batch import and migration endpoints.
2. THE SAM template SHALL define an Admin Simulate Lambda function handling POST `/admin/simulate` with IAM policies granting `dynamodb:Scan` on allQuestionDB.
3. THE SAM template SHALL define an Admin Migrate Lambda function handling POST `/admin/migrate` with IAM policies granting `dynamodb:Scan`, `dynamodb:UpdateItem`, and `dynamodb:BatchWriteItem` on allQuestionDB.
4. THE SAM template SHALL define API Gateway events for all admin endpoints (including POST `/admin/migrate`, GET `/admin/coverage`, GET `/admin/stats`, GET `/admin/export`, and PUT `/admin/themes/{questionType}`) with CognitoAuthorizer and OPTIONS method handlers for CORS.
5. THE SAM template SHALL define an Admin Coverage Lambda function handling GET `/admin/coverage` with IAM policies granting `dynamodb:Scan` on allQuestionDB.
6. THE SAM template SHALL define an Admin Themes Lambda function handling PUT `/admin/themes/{questionType}` with IAM policies granting `dynamodb:Scan`, `dynamodb:UpdateItem`, and `dynamodb:BatchWriteItem` on allQuestionDB.
7. THE SAM template SHALL define an Admin Stats Lambda function handling GET `/admin/stats` with IAM policies granting `dynamodb:Scan` on allQuestionDB.
8. THE Admin Lambda functions SHALL include CORS headers consistent with the existing `ALLOWED_ORIGIN` configuration (`https://www.soulreel.net`) on all responses, using the shared `cors_headers` utility.
9. THE Admin Lambda functions SHALL use the `TABLE_ALL_QUESTIONS` environment variable (set globally in the SAM template) to reference the allQuestionDB table name.
10. THE SAM template SHALL include KMS decrypt permissions for the Admin Lambda functions consistent with existing functions that access allQuestionDB.
11. THE Admin Lambda functions SHALL use the SharedUtilsLayer for shared utilities (`cors`, `responses`).
12. THE SAM template SHALL define an Admin Export Lambda function handling GET `/admin/export` with IAM policies granting `dynamodb:Scan` on allQuestionDB.

### Requirement 13: CORS and Error Handling

**User Story:** As a frontend developer, I want the admin API to follow the same CORS and error handling patterns as the rest of the application, so that the admin tool integrates seamlessly.

#### Acceptance Criteria

1. THE Admin_API Lambda functions SHALL return CORS headers on all responses (200, 4xx, 5xx) using the shared `cors_headers(event)` utility from the SharedUtilsLayer.
2. THE Admin_API Lambda functions SHALL handle OPTIONS preflight requests and return appropriate CORS headers.
3. IF a DynamoDB operation fails in any Admin_API Lambda, THEN THE Admin_API SHALL log the detailed error to CloudWatch and return a generic error message to the client using the shared `error_response` utility.
4. THE Admin_API Lambda functions SHALL include `import os` at the top of each `app.py` file, consistent with the project's CORS rules.
5. THE Admin_API Lambda functions SHALL use the `DecimalEncoder` JSON encoder when serializing DynamoDB responses containing `Decimal` types.

### Requirement 14: Initial Migration of Existing Questions

**User Story:** As an admin, I want existing questions in allQuestionDB to be gracefully handled when the admin tool is first deployed, so that the current behavior (all users see all questions) is preserved without requiring manual tagging of every existing question.

#### Acceptance Criteria

1. WHEN the Admin_Tool first loads questions from allQuestionDB, THE Admin_Tool SHALL treat missing `requiredLifeEvents` attributes as empty lists (`[]`), missing `isInstanceable` as `false`, and missing `instancePlaceholder` as empty string.
2. THE Admin_API SHALL provide a one-time migration endpoint (POST `/admin/migrate`) that scans all Question_Records in allQuestionDB and adds default values for any missing new attributes: `requiredLifeEvents: []`, `isInstanceable: false`, `instancePlaceholder: ""`, `lastModifiedBy: "system-migration"`, `lastModifiedAt: <current timestamp>`. The migration endpoint SHALL skip records that already have these attributes set.
3. THE Admin_Tool SHALL display a migration banner when the Admin_Tool detects that questions are missing the new attributes, offering a one-click "Initialize All Questions" action that calls the migration endpoint.
4. AFTER migration, all existing questions SHALL have empty `requiredLifeEvents` lists, making the questions universally applicable to all users — preserving the current behavior where every user sees every valid question.
5. THE migration endpoint SHALL require CognitoAuthorizer and server-side admin group verification.
6. THE migration endpoint SHALL process questions in batches (using DynamoDB `BatchWriteItem` with 25-item batches) and return a summary of how many records were updated.

### Requirement 15: Life Event Coverage Report

**User Story:** As an admin, I want to see which Life_Event_Keys have questions tagged and which have zero coverage, so that I can identify gaps where a user could select a life event in the survey but receive no relevant questions.

#### Acceptance Criteria

1. THE Admin_Tool SHALL display a "Life Event Coverage" dashboard accessible from the admin navigation at `/admin/coverage`.
2. THE Coverage_Report SHALL list every Life_Event_Key from the Canonical_Life_Event_Registry alongside the count of valid questions (where `Valid` = 1) tagged with that key in `requiredLifeEvents`.
3. THE Coverage_Report SHALL visually highlight Life_Event_Keys with zero tagged questions using a red/warning indicator, making gaps immediately obvious.
4. THE Coverage_Report SHALL show the count of instanceable questions per instanceable Life_Event_Key separately from non-instanceable questions.
5. THE Coverage_Report SHALL show the count of universal questions (questions with empty `requiredLifeEvents`) as a separate summary line.
6. THE Admin_API SHALL expose a GET endpoint at `/admin/coverage` that returns the coverage data (Life_Event_Key to question count mapping) by scanning allQuestionDB and aggregating by `requiredLifeEvents` values.
7. THE Admin_API GET `/admin/coverage` endpoint SHALL require CognitoAuthorizer and server-side admin group verification.

### Requirement 16: Theme-Level Tagging

**User Story:** As an admin, I want to set life event tags at the theme (`questionType`) level and apply them to all questions in that theme at once, so that I can efficiently tag entire groups of questions that share the same life event context.

#### Acceptance Criteria

1. THE Admin_Tool SHALL provide a "Theme Settings" view at `/admin/themes` that lists all distinct `questionType` values from allQuestionDB.
2. FOR each theme, THE Admin_Tool SHALL allow the admin to set default life event tags: `requiredLifeEvents` (multi-select from Canonical_Life_Event_Registry), `isInstanceable` (toggle), and `instancePlaceholder` (dropdown from valid placeholders).
3. WHEN the admin sets or changes theme-level tags and clicks "Apply to All Questions in Theme", THE Admin_API SHALL update all Question_Records with that `questionType` to use the specified `requiredLifeEvents`, `isInstanceable`, and `instancePlaceholder` values.
4. THE Admin_Tool SHALL display a confirmation dialog before applying theme-level tags, showing the count of questions that will be affected.
5. WHEN a new question is created (single or batch) with a `questionType` that has Theme_Defaults set, THE Admin_Tool SHALL pre-populate the life event tag fields with the Theme_Defaults. The admin can override these defaults for individual questions.
6. THE Admin_Tool SHALL allow individual question-level overrides of theme-level tags — the Theme_Defaults are a convenience for bulk operations, not a constraint on individual questions.
7. THE Admin_API SHALL expose a PUT endpoint at `/admin/themes/{questionType}` that applies the specified life event settings to all Question_Records with that `questionType`.
8. WHEN the theme update endpoint processes questions, THE Admin_API SHALL set `lastModifiedBy` to the admin user's email (from the JWT `email` claim) and `lastModifiedAt` to the current UTC timestamp on each affected Question_Record.
9. THE Admin_API PUT `/admin/themes/{questionType}` endpoint SHALL require CognitoAuthorizer and server-side admin group verification.
10. THE theme-level settings SHALL be applied directly to Question_Records and are not stored separately. The Theme_Defaults are derived from the current state of questions in that theme, not from a separate metadata store.

### Requirement 17: Admin Dashboard Summary Page

**User Story:** As an admin, I want a summary dashboard as the default landing page, so that I can see an at-a-glance overview of the question bank health, identify coverage gaps by theme and difficulty, and navigate directly to problem areas.

#### Acceptance Criteria

1. THE Admin_Tool SHALL display a "Dashboard" summary page as the default landing page at `/admin` (or `/admin/dashboard`).
2. THE summary page SHALL display top-level stat cards showing: total questions (valid + invalid), total valid questions, total invalid questions, number of distinct question types, number of difficulty levels in use, number of Life_Event_Keys with zero tagged questions (sourced from Coverage_Report data), and number of instanceable questions.
3. THE summary page SHALL display a Question Type × Difficulty grid table where rows are distinct `questionType` values (sorted alphabetically), columns are difficulty levels 1 through 10, and each cell shows the count of valid questions matching that `questionType` and `Difficulty` combination.
4. THE grid SHALL display a row total at the end of each row showing the total valid questions for that question type.
5. THE grid SHALL display a column total at the bottom of each column showing the total valid questions at that difficulty level.
6. THE grid SHALL display a grand total in the bottom-right corner showing the total count of all valid questions.
7. THE grid SHALL visually highlight cells with zero questions (e.g., gray background or dash) to make gaps immediately visible.
8. WHEN the admin clicks a cell in the grid, THE Admin_Tool SHALL navigate to the question browse view at `/admin/questions` pre-filtered to that `questionType` and `Difficulty` level.
9. THE Admin_API SHALL expose a GET endpoint at `/admin/stats` that returns the aggregated data needed for the summary page (question counts by type and difficulty, life event coverage counts, instanceable counts).
10. THE Admin_API GET `/admin/stats` endpoint SHALL require CognitoAuthorizer and server-side admin group verification.

### Requirement 18: Export and Backup

**User Story:** As an admin, I want to export the question bank to CSV or JSON, so that I have a backup and can review questions offline.

#### Acceptance Criteria

1. THE Admin_Tool SHALL provide an "Export" button accessible from the question browse view and the dashboard.
2. THE Admin_Tool SHALL support exporting to CSV format (one row per question, all attributes as columns) and JSON format (array of Question_Record objects).
3. THE export SHALL respect the current filter criteria — if the admin has filtered to a specific questionType or difficulty, only the filtered questions are exported. An "Export All" option SHALL also be available.
4. THE Admin_API SHALL expose a GET endpoint at `/admin/export` that returns all Question_Records (or filtered subset) in the requested format (CSV or JSON), specified via a `format` query parameter.
5. THE Admin_API export endpoint SHALL require CognitoAuthorizer and server-side admin group verification.
6. THE export SHALL include all attributes: `questionId`, `questionType`, `Difficulty`, `Valid`, `Question`, `requiredLifeEvents` (comma-separated in CSV), `isInstanceable`, `instancePlaceholder`, `lastModifiedBy`, `lastModifiedAt`.
