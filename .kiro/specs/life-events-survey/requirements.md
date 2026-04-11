# Requirements Document

## Introduction

SoulReel currently serves every legacy maker the same static set of questions from the `allQuestionDB` DynamoDB table. Questions are organized by `questionType` (theme) and `Difficulty` (level 1–10), and every recorded video links back to the exact `questionId`. This approach guarantees editorial control, auditing, and a 1:1 match between videos and questions.

However, many questions are irrelevant to individual users because the question set does not account for major life events (marriage, children, loss, career changes, etc.). Users see generic questions that do not reflect their lived experience.

This feature adds a short, mandatory life-events survey that runs once per user — before they can access the recording flow. After submission, a backend function filters the existing static QuestionBank so each user only sees questions relevant to their selected life events. No questions are dynamically generated; every question remains 100% under editorial control in the spreadsheet/DynamoDB pipeline.

Some life events can happen multiple times (multiple marriages, multiple children, multiple losses). For these repeatable events, the system uses Question Instancing: template questions in the QuestionBank contain placeholder tokens (e.g., `{spouse_name}`) that get stamped out into personalized instances at assignment time. The survey collects the number of occurrences and a name for each instance. At assignment time, each instanceable question is duplicated per named instance, and the placeholder in the question text is replaced with the instance name. This preserves full editorial control — the `questionId` still points to the exact template in the QuestionBank — while delivering personalized, per-person question sets.

For the `got_married` event, each spouse instance also carries a status (`married`, `divorced`, or `deceased`) that enables status-aware question filtering. Questions tagged with status-derived Life_Event_Keys (e.g., `spouse_divorced`) are only stamped out for instances matching that status, while questions tagged with the base `got_married` key apply to all spouse instances regardless of status.

## Glossary

- **Survey_Service**: The backend Lambda function that receives the user's completed life-events survey, validates it, and stores the selected events and life event instances in the user's profile.
- **Question_Assignment_Service**: The backend Lambda function that queries `allQuestionDB`, filters questions by matching the user's selected life events against each question's `requiredLifeEvents` attribute, stamps out instanced copies of Instanceable_Questions per named instance, and writes the resulting `assignedQuestions` structure to the user's profile.
- **Survey_UI**: The frontend React component that presents the life-events survey as a floating card overlay on top of the Dashboard screen, showing one category of events at a time with animated transitions between steps.
- **Survey_Gate**: The frontend logic that displays the Survey_UI overlay on the Dashboard when `hasCompletedSurvey` is `false` in the user's profile, preventing interaction with the Dashboard until the survey is completed.
- **allQuestionDB**: The existing DynamoDB table containing all questions with attributes including `questionId`, `questionType`, `Difficulty`, `Valid`, `Question`, `isInstanceable`, and `instancePlaceholder`.
- **userStatusDB**: The existing DynamoDB table storing per-user global state including `currLevel`.
- **userQuestionLevelProgressDB**: The existing DynamoDB table tracking per-user, per-questionType progress including remaining questions at the current level.
- **Life_Event_Key**: A unique string identifier for each life event option in the survey (e.g., `got_married`, `death_of_child`, `first_job`). For consolidated events with sub-checkboxes, each sub-option has its own granular Life_Event_Key (e.g., `death_of_child`, `death_of_parent`, `death_of_sibling`, `death_of_friend_mentor`). Status-derived keys (`spouse_divorced`, `spouse_deceased`, `spouse_still_married`) are virtual Life_Event_Keys generated from the `got_married` instance statuses and used for status-aware question filtering.
- **Consolidated_Event**: A life event in the Survey_UI that displays as a single card/item with a parent label and multiple sub-checkboxes. The parent item groups related experiences under one heading, while each sub-checkbox maps to its own granular Life_Event_Key for precise question filtering.
- **Legacy_Maker**: A user with `persona_type` of `legacy_maker` who creates video responses to questions.
- **requiredLifeEvents**: An array attribute on each question in `allQuestionDB` listing Life_Event_Keys that must ALL be present in the user's selected events for the question to be assigned.
- **assignedQuestions**: A structured object stored in `userStatusDB` containing two sections: `standard` (a flat list of questionId values for non-instanceable questions) and `instanced` (an array of instance group objects, each containing `eventKey`, `instanceName`, `instanceOrdinal`, and `questionIds`).
- **hasCompletedSurvey**: A boolean flag stored in `userStatusDB` indicating whether the user has completed the life-events survey.
- **Instanceable_Question**: A question in `allQuestionDB` with `isInstanceable` set to `true` and an `instancePlaceholder` value. The `Question` text contains a placeholder token (e.g., `{spouse_name}`) that is replaced with a specific instance name at display time. The `questionId` always references the template; instancing is resolved at assignment and display time.
- **instancePlaceholder**: A string attribute on an Instanceable_Question in `allQuestionDB` specifying the placeholder token used in the question text (e.g., `{spouse_name}`, `{child_name}`, `{deceased_name}`).
- **instanceKey**: A composite string identifier in the format `<eventKey>:<ordinal>` (e.g., `got_married:1`, `death_of_friend_mentor:2`) that, combined with a `questionId`, uniquely identifies a specific instanced video response. The ordinal is guaranteed unique within an eventKey. The instance name is a display label stored in `lifeEventInstances` and is not part of the key. Stored alongside the `questionId` in video response records.
- **lifeEventInstances**: An array attribute stored in `userStatusDB` containing structured instance data for repeatable life events. Each entry contains an `eventKey` (Life_Event_Key), and an `instances` array of objects with `name` (string), `ordinal` (number), and optionally `status` (string) fields. For `got_married` instances, the `status` field is required and must be one of `married`, `divorced`, or `deceased`.
- **Instance_Status**: An optional string attribute on an instance within `lifeEventInstances` that further qualifies the instance. For `got_married`, valid statuses are `married`, `divorced`, and `deceased`. The Question_Assignment_Service uses the status to match status-aware Life_Event_Keys (e.g., `spouse_divorced` matches instances with status `divorced`).

## Requirements

### Requirement 1: Life-Events Survey Data Model

**User Story:** As a system administrator, I want each question in the QuestionBank to carry life-event metadata and instancing attributes, so that questions can be filtered based on a user's life experiences and stamped out per named instance for repeatable events.

#### Acceptance Criteria

1. THE allQuestionDB table SHALL include a `requiredLifeEvents` attribute (list of strings) on every question record.
2. WHEN a question has an empty `requiredLifeEvents` list, THE Question_Assignment_Service SHALL treat the question as universally applicable to all users regardless of their selected life events.
3. THE allQuestionDB table SHALL store each life event value as a Life_Event_Key matching the canonical key defined in the survey configuration.
4. THE Question Management Admin Tool SHALL enforce that `requiredLifeEvents` values are valid Life_Event_Keys from the canonical registry when editing or creating questions.
5. THE allQuestionDB table SHALL include an `isInstanceable` attribute (boolean) on every question record, defaulting to `false`.
6. THE allQuestionDB table SHALL include an `instancePlaceholder` attribute (string) on every question record where `isInstanceable` is `true`, specifying the placeholder token used in the question text (e.g., `{spouse_name}`, `{child_name}`, `{deceased_name}`).
7. WHEN `isInstanceable` is `true`, THE `Question` text attribute SHALL contain the `instancePlaceholder` token at least once, to be replaced with the instance name at display time.
8. WHEN `isInstanceable` is `false` or absent, THE Question_Assignment_Service SHALL treat the question as a standard non-instanceable question with no placeholder substitution.

### Requirement 2: User Survey Profile Storage

**User Story:** As a legacy maker, I want my life-event selections and instance details to be stored in my profile, so that the system can personalize my question set with per-person questions.

#### Acceptance Criteria

1. THE userStatusDB table SHALL include a `hasCompletedSurvey` attribute (boolean) for each Legacy_Maker, defaulting to `false`.
2. THE userStatusDB table SHALL include a `selectedLifeEvents` attribute (list of strings) storing the Life_Event_Keys the user selected.
3. THE userStatusDB table SHALL include a `surveyCompletedAt` attribute (ISO 8601 timestamp string) recording when the survey was submitted.
4. THE userStatusDB table SHALL include an `assignedQuestions` attribute (map) with two keys: `standard` (list of questionId strings for non-instanceable questions) and `instanced` (list of instance group objects, each containing `eventKey` (string), `instanceName` (string for display), `instanceOrdinal` (number, the key identifier), and `questionIds` (list of questionId strings)).
5. WHERE a user provides free-text input for the "other life event" option, THE userStatusDB table SHALL store the free-text value in a `customLifeEvent` attribute (string).
6. THE userStatusDB table SHALL include a `lifeEventInstances` attribute (list of maps) storing the instance data for repeatable life events, where each map contains `eventKey` (string) and `instances` (list of maps each containing `name` (string), `ordinal` (number), and optionally `status` (string)). For `got_married` instances, the `status` field is required and must be one of `married`, `divorced`, or `deceased`.

### Requirement 3: Survey UI Presentation

**User Story:** As a legacy maker, I want to complete a step-by-step life-events survey that floats over the Dashboard, so that I can quickly indicate which events apply to my life without leaving the main screen.

#### Acceptance Criteria

1. THE Survey_UI SHALL render as a floating card overlay centered on top of the Dashboard screen, with the Dashboard visible but dimmed and non-interactive behind a semi-transparent backdrop.
2. THE Survey_UI SHALL present life events one category at a time across seven steps: "Core Relationship & Family Events", "Education & Early Life Milestones", "Career & Professional Life", "Health & Personal Resilience", "Relocation & Life Transitions", "Spiritual, Creative & Legacy Moments", and "Other High-Impact Events".
3. THE Survey_UI SHALL render each life event within the current category step as a labeled checkbox (or yes/no toggle) with a descriptive subtitle.
4. THE Survey_UI SHALL render Consolidated_Events as a single card/item with a parent label and descriptive subtitle, followed by indented sub-checkboxes for each sub-option; selecting any sub-checkbox SHALL record the corresponding granular Life_Event_Key in the user's selections.
5. THE Survey_UI SHALL include a free-text input field in the "Other High-Impact Events" step for users to describe a custom turning-point event with an optional year.
6. THE Survey_UI SHALL allow the user to select zero or more events within each category step (no minimum required per step).
7. THE Survey_UI SHALL display a "Next" button to advance to the next category step and a "Back" button to return to the previous step (hidden on the first step).
8. THE Survey_UI SHALL display a progress indicator (e.g., step counter "3 of 7" or progress bar) showing the user's current position within the total number of steps.
9. WHEN the user advances to the next step or returns to the previous step, THE Survey_UI SHALL animate the transition between category cards with a smooth slide or fade animation.
10. THE Survey_UI SHALL display a "Submit" button on the final step that is enabled at all times, allowing submission even with zero total selections across all steps.
11. THE Survey_UI SHALL be responsive, rendering the floating card correctly on mobile viewports (below 640px width, card fills most of the screen) and desktop viewports (card is centered with constrained max-width).
12. THE Survey_UI SHALL use the existing SoulReel design system (Tailwind classes, `legacy-purple` and `legacy-navy` color tokens, shadcn/ui components).
13. THE Survey_UI SHALL prevent the user from closing or dismissing the overlay without completing or submitting the survey (no close button, no click-outside-to-dismiss).
14. WHEN the user clicks Submit, THE Survey_UI SHALL display a processing state within the overlay card showing a loading spinner and a message such as "Personalizing your questions..." while the backend processes the submission and assignment.
15. THE Survey_UI SHALL keep the overlay visible and non-dismissable during the processing state.
16. WHEN the backend returns a successful response, THE Survey_UI SHALL briefly display a success message (e.g., "Your personalized questions are ready!" with the assigned question count) before the overlay dismisses.
17. THE Survey_UI SHALL disable the Submit button and show a loading spinner while the submission request is in flight, to prevent duplicate submissions.
18. WHEN the survey submission POST request fails (network error, HTTP 4xx, or HTTP 5xx), THE Survey_UI SHALL display an error toast/notification with a user-friendly message (e.g., "Something went wrong. Please try again.").
19. WHEN the survey submission fails, THE Survey_UI SHALL keep the overlay open with the user's selections preserved, and re-enable the Submit button so the user can retry.
20. THE Survey_UI SHALL present the following life events organized by category:

    **Step 1 — Core Relationship & Family Events:**
    - "Got married or entered a long-term partnership" (`got_married`)
    - "Had children (biological, adopted, step, or foster)" (`had_children`)
    - "Became a grandparent" (`became_grandparent`)
    - "Experienced the death of someone close" — Consolidated_Event with sub-checkboxes: Child (`death_of_child`), Parent (`death_of_parent`), Sibling or close family member (`death_of_sibling`), Close friend or mentor (`death_of_friend_mentor`)
    - "Became estranged from a family member" (`estranged_family_member`)
    - "Experienced infertility or pregnancy loss" (`infertility_or_pregnancy_loss`)
    - "Raised a child with special needs" (`raised_child_special_needs`)
    - "Had a significant falling out with a close friend" (`falling_out_close_friend`)

    **Step 2 — Education & Early Life Milestones:**
    - "Graduated from high school" (`graduated_high_school`)
    - "Graduated from college or university" (`graduated_college`)
    - "Earned a graduate or professional degree" (`graduate_degree`)
    - "Studied abroad or had a formative travel experience" (`studied_abroad`)
    - "Had a teacher or mentor who changed your trajectory" (`influential_mentor`)

    **Step 3 — Career & Professional Life:**
    - "Started your first real job" (`first_job`)
    - "Changed careers or industries" (`career_change`)
    - "Started your own business or became self-employed" (`started_business`)
    - "Got fired or laid off" (`got_fired`)
    - "Retired from your primary career" (`retired`)
    - "Became a mentor or teacher" (`became_mentor`)

    **Step 4 — Health & Personal Resilience:**
    - "Overcame a serious illness or injury" (`serious_illness`)
    - "Dealt with a mental health challenge" (`mental_health_challenge`)
    - "Cared for an aging or ill family member" (`caregiver`)
    - "Went through addiction or recovery" (`addiction_recovery`)
    - "Experienced financial hardship or bankruptcy" (`financial_hardship`)
    - "Went through a major legal issue" (`major_legal_issue`)

    **Step 5 — Relocation & Life Transitions:**
    - "Moved to a new city or state" (`moved_city`)
    - "Immigrated to a new country" (`immigrated`)
    - "Lived abroad for an extended period" (`lived_abroad`)
    - "Learned a second language or became bilingual" (`learned_second_language`)

    **Step 6 — Spiritual, Creative & Legacy Moments:**
    - "Had a spiritual awakening or deepened your faith" (`spiritual_awakening`)
    - "Left or changed your religion" (`changed_religion`)
    - "Completed a creative work you are proud of" (`creative_work`)
    - "Received a major award or public recognition" (`major_award`)
    - "Experienced racism, discrimination, or a civil rights moment" (`experienced_discrimination`)

    **Step 7 — Other High-Impact Events:**
    - "Served in the military" (`military_service`)
    - "Survived a natural disaster or major crisis" (`survived_disaster`)
    - "Had a brush with death or near-death experience" (`near_death`)
    - "Experienced a life-changing act of kindness" (`act_of_kindness`)
    - Free-text input for a custom turning-point event with optional year (`other`)

21. WHEN the user selects the `got_married` life event, THE Survey_UI SHALL display a follow-up within the same card/step asking "How many times have you been married or in a long-term partnership?" via a number picker (minimum 1, maximum 10), and for each spouse: a name input field using ordinal labels (e.g., "What was your first spouse's/partner's name?") and a status dropdown with options: "Still married/together" (value: `married`), "Divorced/separated" (value: `divorced`), "They passed away" (value: `deceased`).
22. WHEN the user selects an instanceable life event other than `got_married` (`had_children`, `death_of_child`, `death_of_parent`, `death_of_sibling`, `death_of_friend_mentor`), THE Survey_UI SHALL display a follow-up within the same card/step asking "How many times?" via a number picker (minimum 1, maximum 10), and a name input field for each instance using ordinal labels (e.g., "What is your first child's name?" for `had_children`; "What was the name of the first [relationship] you lost?" for death sub-events). These instanceable events use the simple name-only flow with no status dropdown.
23. THE Survey_UI SHALL require the user to provide a non-empty name for each instance of an instanceable life event, and a valid status selection for each `got_married` instance, before allowing progression to the next step or submission.
24. THE Survey_UI SHALL recognize the following Life_Event_Keys as instanceable with their corresponding placeholders: `got_married` (`{spouse_name}`), `had_children` (`{child_name}`), `death_of_child` (`{deceased_name}`), `death_of_parent` (`{deceased_name}`), `death_of_sibling` (`{deceased_name}`), `death_of_friend_mentor` (`{deceased_name}`).

### Requirement 4: Survey Gating

**User Story:** As a product owner, I want legacy makers to complete the life-events survey before interacting with the Dashboard or recording flow, so that every user gets a personalized question set.

#### Acceptance Criteria

1. WHEN a Legacy_Maker with `hasCompletedSurvey` equal to `false` navigates to the Dashboard, THE Survey_Gate SHALL display the Survey_UI overlay on top of the Dashboard, preventing interaction with Dashboard controls until the survey is submitted.
2. WHEN a Legacy_Maker with `hasCompletedSurvey` equal to `false` navigates to any other protected route (RecordResponse, RecordConversation, QuestionThemes, ManageBenefactors), THE Survey_Gate SHALL redirect the user to the Dashboard where the Survey_UI overlay is displayed.
3. WHEN a Legacy_Maker submits the survey successfully, THE Survey_Gate SHALL dismiss the Survey_UI overlay with a fade-out animation and reveal the fully interactive Dashboard beneath.
4. WHEN a Legacy_Maker with `hasCompletedSurvey` equal to `true` navigates to the Dashboard, THE Survey_Gate SHALL not display the Survey_UI overlay.
5. THE Survey_Gate SHALL retrieve the `hasCompletedSurvey` flag from the user's profile on authentication and cache the value in the AuthContext.
6. WHILE the `hasCompletedSurvey` flag is being loaded from the backend, THE Survey_Gate SHALL display a loading indicator and not display the Survey_UI overlay or allow navigation.

### Requirement 5: Survey Submission Processing

**User Story:** As a legacy maker, I want my survey responses and instance details to be saved and processed, so that I receive a personalized question set with per-person questions.

#### Acceptance Criteria

1. WHEN the user submits the survey, THE Survey_Service SHALL validate that the request body contains a `selectedLifeEvents` array of strings.
2. WHEN the user submits the survey, THE Survey_Service SHALL validate that every string in `selectedLifeEvents` is a recognized Life_Event_Key or the special value `other`.
3. WHEN validation succeeds, THE Survey_Service SHALL write `selectedLifeEvents`, `hasCompletedSurvey` set to `true`, and `surveyCompletedAt` set to the current UTC timestamp to the user's record in userStatusDB.
4. IF the request body contains an invalid or missing `selectedLifeEvents` field, THEN THE Survey_Service SHALL return HTTP 400 with a descriptive error message.
5. IF a DynamoDB write fails during survey submission, THEN THE Survey_Service SHALL return HTTP 500 with a generic error message and log the detailed error to CloudWatch.
6. THE Survey_Service SHALL authenticate the user via the Cognito JWT token and use the `sub` claim as the user identifier.
7. WHEN the request body contains a `lifeEventInstances` array, THE Survey_Service SHALL validate that each entry contains a valid `eventKey` (a recognized instanceable Life_Event_Key) and a non-empty `instances` array where each instance has a non-empty `name` (string) and a positive integer `ordinal`.
8. WHEN validation succeeds and `lifeEventInstances` is present, THE Survey_Service SHALL write the `lifeEventInstances` array to the user's record in userStatusDB alongside the other survey fields.
9. IF the `lifeEventInstances` array contains an entry with an `eventKey` that is not a recognized instanceable Life_Event_Key, THEN THE Survey_Service SHALL return HTTP 400 with a descriptive error message.
10. WHEN writing survey data to userStatusDB, THE Survey_Service SHALL use a DynamoDB UpdateItem operation (not PutItem) to add `selectedLifeEvents`, `hasCompletedSurvey`, `surveyCompletedAt`, `lifeEventInstances`, and `assignedQuestions` to the existing user record without overwriting other attributes (e.g., `currLevel`, `allowTranscription`).
11. WHEN the `lifeEventInstances` array contains an entry with `eventKey` equal to `got_married`, THE Survey_Service SHALL validate that each instance in that entry includes a `status` field with a value of `married`, `divorced`, or `deceased`.
12. IF a `got_married` instance is missing the `status` field or has an invalid status value, THEN THE Survey_Service SHALL return HTTP 400 with a descriptive error message.

### Requirement 6: Question Assignment After Survey

**User Story:** As a legacy maker, I want the system to automatically assign me relevant questions after I complete the survey, including per-person instanced questions for repeatable life events, so that I only see questions that match my life experiences.

#### Acceptance Criteria

1. WHEN the Survey_Service successfully stores the user's survey responses, THE Question_Assignment_Service SHALL query allQuestionDB for all valid questions (where `Valid` equals 1 or `active` equals true).
2. THE Question_Assignment_Service SHALL include a question in the user's assigned set when the question's `requiredLifeEvents` list is empty (universally applicable).
3. THE Question_Assignment_Service SHALL include a question in the user's assigned set when every Life_Event_Key in the question's `requiredLifeEvents` list is present in the user's `selectedLifeEvents` or derivable from the user's instance statuses.
4. THE Question_Assignment_Service SHALL exclude a question from the user's assigned set when one or more Life_Event_Keys in the question's `requiredLifeEvents` list are absent from the user's `selectedLifeEvents` and not derivable from instance statuses.
5. WHEN a matched question has `isInstanceable` equal to `false` or absent, THE Question_Assignment_Service SHALL add the question's `questionId` to the `assignedQuestions.standard` list.
6. WHEN a matched question has `isInstanceable` equal to `true`, THE Question_Assignment_Service SHALL stamp out one instance group per named instance from the user's `lifeEventInstances` for the matching `eventKey`, adding the question's `questionId` to each instance group's `questionIds` list.
7. THE Question_Assignment_Service SHALL write the resulting `assignedQuestions` object to the user's userStatusDB record in the structured format: `{ standard: [questionId, ...], instanced: [{ eventKey, instanceName, instanceOrdinal, questionIds: [questionId, ...] }, ...] }`.
8. THE Question_Assignment_Service SHALL order instance groups within `assignedQuestions.instanced` by `eventKey` then by `instanceOrdinal` ascending.
9. WHEN a question's `requiredLifeEvents` includes a status-aware Life_Event_Key (`spouse_divorced`, `spouse_deceased`, or `spouse_still_married`), THE Question_Assignment_Service SHALL stamp out instanced copies only for `got_married` instances whose `status` matches the key (e.g., `spouse_divorced` matches instances with status `divorced`; `spouse_deceased` matches instances with status `deceased`; `spouse_still_married` matches instances with status `married`).
10. WHEN a question's `requiredLifeEvents` includes the base `got_married` key (without a status qualifier), THE Question_Assignment_Service SHALL stamp out instanced copies for all `got_married` instances regardless of their status.
11. WHEN the assignment is complete for a first-time survey submission, THE Question_Assignment_Service SHALL reinitialize the user's progress records in userQuestionLevelProgressDB to reflect only the assigned questions at difficulty level 1, counting each instanced question copy as a separate question for progress purposes. This reinitialization applies only to first-time survey completion, not retakes.

### Requirement 7: Progress Initialization with Assigned Questions

**User Story:** As a legacy maker, I want my dashboard progress to reflect only my personalized questions including instanced copies, so that I see accurate completion percentages.

#### Acceptance Criteria

1. WHEN a user has a non-empty `assignedQuestions` structure in userStatusDB, THE getProgressSummary2 Lambda SHALL calculate total question count as the sum of `assignedQuestions.standard` length plus the total number of individual questionId entries across all `assignedQuestions.instanced` groups (each instance of a question counts separately).
2. WHEN a user has an empty or missing `assignedQuestions` attribute in userStatusDB, THE getProgressSummary2 Lambda SHALL use all valid questions for progress calculation (current behavior, backward compatible).
3. THE initializeUserProgress Lambda SHALL use the `assignedQuestions` structure (when present) to determine which difficulty-1 questions to include in the initial progress records for each questionType, counting each instanced copy as a separate question.
4. WHEN the user advances to a new difficulty level, THE incrementUserLevel2 Lambda SHALL filter the next level's questions to only those in the user's `assignedQuestions` (both standard and instanced lists).
5. WHEN a diff-based retake adds new questions to `assignedQuestions`, THE getProgressSummary2 Lambda SHALL include the new questions as unanswered in the total count, and WHEN a diff-based retake removes questions from `assignedQuestions`, THE getProgressSummary2 Lambda SHALL exclude the removed questions from the total count.

### Requirement 8: Survey API Endpoint

**User Story:** As a frontend developer, I want a REST API endpoint for submitting the survey, so that the Survey_UI can communicate with the backend.

#### Acceptance Criteria

1. THE Survey_Service SHALL expose a POST endpoint at `/survey/submit` on the existing API Gateway.
2. THE Survey_Service SHALL require Cognito JWT authorization via the existing CognitoAuthorizer.
3. THE Survey_Service SHALL return CORS headers consistent with the existing `ALLOWED_ORIGIN` configuration (`https://www.soulreel.net`).
4. THE Survey_Service SHALL handle OPTIONS preflight requests for the `/survey/submit` path.
5. WHEN the survey is submitted successfully, THE Survey_Service SHALL return HTTP 200 with a JSON body containing `{ "message": "Survey completed", "assignedQuestionCount": <number> }`.
6. THE Survey_Service SHALL accept a request body containing `selectedLifeEvents` (array of strings) and optionally `lifeEventInstances` (array of objects with `eventKey` and `instances` fields) and `customLifeEvent` (string).

### Requirement 9: Survey Status API Endpoint

**User Story:** As a frontend developer, I want an API endpoint to check whether the current user has completed the survey and retrieve their instance data, so that the frontend can enforce gating and pre-populate retake forms.

#### Acceptance Criteria

1. THE Survey_Service SHALL expose a GET endpoint at `/survey/status` on the existing API Gateway.
2. THE Survey_Service SHALL require Cognito JWT authorization via the existing CognitoAuthorizer.
3. WHEN called, THE Survey_Service SHALL return HTTP 200 with a JSON body containing `{ "hasCompletedSurvey": <boolean>, "selectedLifeEvents": <array|null>, "surveyCompletedAt": <string|null>, "lifeEventInstances": <array|null> }`.
4. THE Survey_Service SHALL return CORS headers consistent with the existing `ALLOWED_ORIGIN` configuration.

### Requirement 10: SAM Template and IAM Configuration

**User Story:** As a DevOps engineer, I want the new Lambda functions and DynamoDB changes to be defined in the SAM template, so that deployment is automated and IAM permissions are correct.

#### Acceptance Criteria

1. THE SAM template SHALL define the Survey submission Lambda function with IAM policies granting `dynamodb:UpdateItem` and `dynamodb:GetItem` on userStatusDB, and `dynamodb:Scan` and `dynamodb:Query` on allQuestionDB. Note: `UpdateItem` is used instead of the project's typical `PutItem` pattern because the survey Lambda must add fields (`selectedLifeEvents`, `hasCompletedSurvey`, `surveyCompletedAt`, `lifeEventInstances`, `assignedQuestions`) to the existing user record without overwriting other attributes such as `currLevel` and `allowTranscription`.
2. THE SAM template SHALL define the Survey status Lambda function with IAM policies granting `dynamodb:GetItem` on userStatusDB.
3. THE SAM template SHALL grant the Survey submission Lambda `dynamodb:PutItem` and `dynamodb:Query` on userQuestionLevelProgressDB for reinitializing progress after assignment.
4. THE SAM template SHALL include KMS decrypt permissions for the Survey Lambda functions consistent with existing functions that access userStatusDB.
5. THE SAM template SHALL define API Gateway events for both POST `/survey/submit` and GET `/survey/status` with CognitoAuthorizer and OPTIONS method handlers.

### Requirement 11: Question Management Admin Tool (External Dependency)

**User Story:** As a content editor, I want a dedicated admin web application for managing questions, so that I can tag questions with life events, toggle validity, edit question text, and batch-import AI-generated questions with full validation — replacing the error-prone Excel spreadsheet workflow.

#### Acceptance Criteria

1. A separate Question Management Admin Tool SHALL be built and deployed as a prerequisite to the life-events survey feature. This admin tool is defined in its own spec at `.kiro/specs/question-admin-tool/`.
2. THE admin tool SHALL allow editors to set `requiredLifeEvents` on each question using a dropdown/autocomplete from the canonical Life_Event_Key registry, preventing typos and invalid keys.
3. THE admin tool SHALL allow editors to set `isInstanceable` and `instancePlaceholder` on each question, with validation that instanceable questions contain the placeholder token in their question text.
4. THE admin tool SHALL support batch import of AI-generated questions with bulk assignment of theme, difficulty, and life event tags.
5. THE admin tool SHALL include a preview/simulator feature that shows which questions a user with a given set of life events would be assigned, enabling verification of the filtering logic before it affects real users.
6. ALL existing questions in allQuestionDB SHALL be tagged with appropriate `requiredLifeEvents`, `isInstanceable`, and `instancePlaceholder` values using the admin tool BEFORE the life-events survey feature is deployed to production.
7. THE admin tool SHALL write directly to allQuestionDB, replacing the Excel-to-JSON-to-DynamoDB migration pipeline entirely.

### Requirement 12: Backward Compatibility

**User Story:** As an existing user, I want the app to continue working normally if I have not yet taken the survey or have no instanced data, so that the rollout does not break my experience.

#### Acceptance Criteria

1. WHEN a Legacy_Maker's userStatusDB record has no `hasCompletedSurvey` attribute, THE Survey_Gate SHALL treat the value as `false` and display the Survey_UI overlay on the Dashboard.
2. WHEN a Legacy_Maker's userStatusDB record has no `assignedQuestions` attribute, THE getProgressSummary2 Lambda SHALL use all valid questions for progress calculation (current behavior).
3. WHEN a Legacy_Maker's userStatusDB record has no `assignedQuestions` attribute, THE initializeUserProgress Lambda SHALL use all valid difficulty-1 questions (current behavior).
4. THE existing `questionId` linkage in userQuestionStatusDB (video response records) SHALL remain unchanged; every video response continues to reference the exact questionId shown.
5. WHEN a Legacy_Maker's userStatusDB record has no `lifeEventInstances` attribute, THE Question_Assignment_Service SHALL treat the value as an empty list and assign only non-instanceable questions (all matched questions go to `assignedQuestions.standard`).
6. WHEN a Legacy_Maker's `assignedQuestions` attribute is a flat list of strings (legacy format) instead of the structured map format, THE getProgressSummary2 Lambda SHALL treat the flat list as equivalent to `{ standard: <the flat list>, instanced: [] }`.

### Requirement 13: Survey Retake Capability

**User Story:** As a legacy maker, I want the option to retake the survey if my life circumstances change, so that my question set and instances stay relevant over time.

#### Acceptance Criteria

1. THE Dashboard SHALL display a "Retake Life Events Survey" link or button accessible from the user's profile or settings area.
2. WHEN a user initiates a survey retake, THE Survey_UI SHALL open as a floating card overlay on the Dashboard and pre-populate checkboxes with the user's previously selected life events from `selectedLifeEvents`, and pre-populate instance names and counts from the user's existing `lifeEventInstances`.
3. WHEN a user submits a retaken survey, THE Survey_Service SHALL overwrite the existing `selectedLifeEvents`, `lifeEventInstances`, and `surveyCompletedAt` in userStatusDB.
4. WHEN a user submits a retaken survey, THE Question_Assignment_Service SHALL compute new `assignedQuestions` based on the new selections and new instances, and perform a diff against the old `assignedQuestions`.
5. WHEN `assignedQuestions` changes after a retake, THE Question_Assignment_Service SHALL perform a diff-based update: questions present in both old and new assigned sets retain their existing progress in userQuestionLevelProgressDB; questions present only in the new set are added to progress tracking at the user's current difficulty level for that questionType and marked as unanswered; questions present only in the old set are removed from `assignedQuestions` but their video responses in userQuestionStatusDB are preserved.
6. IF a question was previously assigned and answered but is no longer in the new `assignedQuestions` list, THEN THE Question_Assignment_Service SHALL retain the video response record in userQuestionStatusDB (no data deletion).
7. IF instances change after a retake (e.g., user adds a third spouse or removes one), THE Question_Assignment_Service SHALL perform a diff-based update on instanced assignments: new instances get their questions added to progress tracking as unanswered at the user's current difficulty level; removed instances have their questions removed from `assignedQuestions.instanced` only (video responses in userQuestionStatusDB are preserved); kept instances retain their existing progress. The diff uses `questionId + instanceKey` (ordinal-based) as the composite identifier for instanced questions.

### Requirement 14: Question Instance Grouping and Display

**User Story:** As a legacy maker, I want instanced questions to be grouped by person and displayed with personalized text, so that I can answer all questions about one person before moving to the next.

#### Acceptance Criteria

1. THE recording flow SHALL present instanced questions grouped by instance — all questions for one instance (e.g., all of Sarah's marriage questions) SHALL be displayed together as a contiguous block before any questions for the next instance (e.g., David's marriage questions).
2. THE recording flow SHALL present instanced questions in the order defined by `assignedQuestions.instanced`: first by `eventKey`, then by `instanceOrdinal`, then by the order of `questionIds` within each instance group. Questions SHALL NOT be randomly shuffled within an instance group.
3. THE recording flow SHALL present all questions for one instance group before moving to the next instance group.
4. WHEN rendering an Instanceable_Question, THE Survey_UI SHALL replace the `instancePlaceholder` token in the question text with the `instanceName` from the corresponding instance group (e.g., "How did you meet {spouse_name}?" becomes "How did you meet Sarah?").
5. THE recording flow SHALL not interleave questions from different instances — all questionIds within a single instance group SHALL be presented consecutively.
6. THE recording flow SHALL present all instanced question groups for a given questionType before or after the standard questions for that questionType (not interleaved).
7. FOR non-instanced (standard) questions, THE recording flow MAY continue to present questions in random order within a questionType (current behavior).
8. WHEN a video response is recorded for an instanced question, THE Survey_UI SHALL store the `instanceKey` (format: `<eventKey>:<ordinal>`, e.g., `got_married:1`, `got_married:2`) alongside the `questionId` in the video response record in userQuestionStatusDB, using the composite sort key format `{questionId}#{instanceKey}`. The frontend looks up the instance name from `lifeEventInstances` when it needs to display it.
9. THE combination of `questionId` and `instanceKey` SHALL uniquely identify a video response for an instanced question; the `questionId` alone references the template in allQuestionDB, preserving editorial control and auditability. The ordinal-based `instanceKey` format guarantees uniqueness even when multiple instances share the same name.
10. WHEN a video response is recorded for a non-instanced (standard) question, THE Survey_UI SHALL store the `questionId` without an `instanceKey` (or with `instanceKey` set to `null`), maintaining backward compatibility with existing response records.


### Requirement 15: Question-Serving Lambda Filtering by Assigned Questions

**User Story:** As a legacy maker, I want the question-serving Lambda to only return questions from my assigned set, so that I only see personalized questions in the recording flow.

#### Acceptance Criteria

1. WHEN a user has a non-empty `assignedQuestions` structure in userStatusDB, THE getUnansweredQuestionsFromUser Lambda SHALL filter the returned questions to only those whose `questionId` appears in the user's `assignedQuestions` (either in `assignedQuestions.standard` or in any `assignedQuestions.instanced[].questionIds`).
2. WHEN a user has an empty or missing `assignedQuestions` attribute in userStatusDB, THE getUnansweredQuestionsFromUser Lambda SHALL return all valid unanswered questions for the requested questionType (current behavior, backward compatible).
3. THE getUnansweredQuestionsFromUser Lambda SHALL read the user's `assignedQuestions` from userStatusDB by performing a `GetItem` on the user's record.
4. THE SAM template SHALL grant the getUnansweredQuestionsFromUser Lambda `dynamodb:GetItem` on userStatusDB (in addition to its existing permissions on allQuestionDB and userQuestionStatusDB).

### Requirement 16: Composite Sort Key for Instanced Video Responses

**User Story:** As a system architect, I want the video response storage to support multiple responses to the same template question for different instances, so that instanced questions don't overwrite each other.

#### Acceptance Criteria

1. WHEN a video response is recorded for an instanced question, THE uploadVideoResponse Lambda SHALL store the record in userQuestionStatusDB with the sort key set to `{questionId}#{instanceKey}` (e.g., `Q-MAR-001#got_married:1`). The `instanceKey` uses the ordinal-based format `<eventKey>:<ordinal>`.
2. WHEN a video response is recorded for a non-instanced (standard) question, THE uploadVideoResponse Lambda SHALL store the record with the sort key set to the plain `questionId` (no `#` suffix), maintaining backward compatibility with existing records.
3. THE uploadVideoResponse Lambda SHALL accept an optional `instanceKey` field in the request body. When present, it SHALL be appended to the `questionId` with a `#` separator to form the composite sort key.
4. THE uploadVideoResponse Lambda SHALL store the `instanceKey` as a separate attribute on the record (in addition to using it in the composite sort key) for easy querying and display.
5. THE getUnansweredQuestionsFromUser Lambda SHALL account for the composite sort key format when determining which instanced questions have been answered — it SHALL check for records with sort keys matching `{questionId}#{instanceKey}` for each instanced question.
6. THE update_user_progress function SHALL account for the composite sort key format when updating progress after an instanced question is answered.
7. EXISTING video response records in userQuestionStatusDB (which use plain `questionId` as sort key) SHALL remain valid and accessible — no migration of existing records is required.
8. THE SAM template SHALL ensure the uploadVideoResponse Lambda has the same IAM permissions as before (no new permissions needed — it already has `PutItem` on userQuestionStatusDB).
