# Implementation Plan: Dashboard Content Hub

## Overview

Transform the Dashboard into a content hub with three navigation cards routing to dedicated pages. Backend: extend `GET /survey/status` to return `assignedQuestions`, `instancedProgress`, and `questionDetails`. Frontend: extract ProgressSection, create shared components, build three new pages, add routes, and wire everything together.

## Tasks

- [x] 1. Extend backend `GET /survey/status` and update IAM policies
  - [x] 1.1 Add `assignedQuestions`, `instancedProgress`, and `questionDetails` to `handle_status` response
    - In `SamLambda/functions/surveyFunctions/survey/app.py`, modify `handle_status()` to:
      - Include the full `assignedQuestions` structure from the `userStatusDB` record
      - Query `userQuestionStatusDB` (partition key `userId`) for answered instanced question keys (sort keys containing `#`)
      - `BatchGetItem` from `allQuestionDB` for instanced question IDs to get `questionText`, `difficulty`, `questionType`
      - Return `assignedQuestions`, `instancedProgress: { answeredKeys: [...] }`, and `questionDetails: { questionId: { text, difficulty, questionType } }` in the response body
    - Use the `TABLE_USER_QUESTION_STATUS` env var (add `TABLE_USER_QUESTION_STATUS = os.environ.get('TABLE_USER_QUESTION_STATUS', 'userQuestionStatusDB')` at module level)
    - _Requirements: 8.1, 8.2, 8.3_
  - [x] 1.2 Add IAM policies for `userQuestionStatusDB` Query and `allQuestionDB` BatchGetItem
    - In `SamLambda/template.yml`, under `SurveyFunction.Policies`:
      - Add a new Statement granting `dynamodb:Query` on `arn:aws:dynamodb:${AWS::Region}:${AWS::AccountId}:table/userQuestionStatusDB`
      - Add `dynamodb:BatchGetItem` to the existing `allQuestionDB` policy Statement's Action list
    - _Requirements: 8.1_
  - [x] 1.3 Update `SurveyStatusResponse` TypeScript types in `surveyService.ts`
    - Add `AssignedQuestions`, `InstanceGroup`, `InstancedProgress`, `QuestionDetail` interfaces
    - Extend `SurveyStatusResponse` with `assignedQuestions`, `instancedProgress`, `questionDetails` fields (all nullable)
    - _Requirements: 8.1_

- [x] 2. Extract ProgressSection and create shared components
  - [x] 2.1 Extract `ProgressSection` from `Dashboard.tsx` into `FrontEndCode/src/components/ProgressSection.tsx`
    - Move the `ProgressSection` component to its own file
    - Remove the "Continue Recording" button and `handleContinueRecording` function
    - Remove the `overallProgress` prop and inline overall progress display (handled separately by `OverallProgressSection`)
    - Add proper TypeScript interface for props: `{ user: { id: string; personaType: string }; navigationState?: any }`
    - Export the component for use by Dashboard and LifeStoryReflections page
    - _Requirements: 6.2, 6.3, 6.5, 6.6_
  - [x] 2.2 Create `OverallProgressSection` component at `FrontEndCode/src/components/OverallProgressSection.tsx`
    - Props: `{ completed: number; total: number }`
    - Renders white card with "Your Overall Progress" heading, `InfoTooltip`, and existing `ProgressBar` component
    - Reusable across all four pages
    - _Requirements: 10.1, 10.4_
  - [x] 2.3 Create `ContentPathCard` component at `FrontEndCode/src/components/ContentPathCard.tsx`
    - Props: `title`, `subtitle`, `icon`, `progressLabel`, `levelLabel?`, `accentColor`, `disabled?`, `badge?`, `onClick`
    - White card with `rounded-xl`, `p-6`, left accent border (`border-l-4`), min height 120px on mobile
    - Hover: `shadow-lg` + `hover:scale-[1.01]`; Active: `active:scale-[0.99]`; Focus: `focus-visible:ring-2`
    - Disabled state: `opacity-60 cursor-default`, no hover/active effects
    - Keyboard: `role="button"`, `tabIndex={0}`, Enter and Space trigger `onClick`
    - Chevron right icon on the right side
    - Distinct accents: purple for Life Story, blue for Life Events, amber for Values & Emotions
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_
  - [x] 2.4 Write property test for ContentPathCard keyboard accessibility
    - **Property 4: Content path card keyboard accessibility**
    - **Validates: Requirements 5.5**
  - [x] 2.5 Create `LifeEventGroup` component at `FrontEndCode/src/components/LifeEventGroup.tsx`
    - Props: `eventKey`, `instanceName`, `instanceOrdinal`, `questions` array, `totalQuestions`, `completedQuestions`, `onRecord`
    - White card with left accent border, header showing event label + instance name
    - Progress display: `completedQuestions / totalQuestions` with inline progress bar
    - Expandable question list with checkmark (answered) or circle (unanswered) icons
    - "Record" button navigating to recording flow with unanswered questions
    - Completed state with muted styling when all questions answered
    - _Requirements: 7.2, 7.5, 7.6_

- [x] 3. Create `useLifeEventsProgress` hook
  - [x] 3.1 Implement `useLifeEventsProgress` hook at `FrontEndCode/src/hooks/useLifeEventsProgress.ts`
    - Calls `getSurveyStatus()` (single API call, no N+1)
    - For each instance group in `assignedQuestions.instanced`:
      - Look up each `questionId` in `questionDetails` for text, difficulty, questionType
      - Replace placeholder tokens with `instanceName` using `INSTANCEABLE_KEY_TO_PLACEHOLDER` from registry
      - Check if `questionId#eventKey:ordinal` exists in `instancedProgress.answeredKeys` for `isAnswered`
      - Calculate `minDifficultyLevel` as minimum difficulty across group questions
    - Sort groups: ascending by `minDifficultyLevel`, then alphabetically by `eventKey`
    - Sum `totalQuestions` and `completedQuestions` across all groups
    - Return `UseQueryResult<LifeEventsProgressData>` with React Query, 60s stale time
    - _Requirements: 7.3, 7.4, 7.10, 8.1, 8.2, 8.3_
  - [x] 3.2 Write property test for life event group sorting
    - **Property 5: Life event group sorting**
    - **Validates: Requirements 7.3**
  - [x] 3.3 Write property test for life event grouping completeness
    - **Property 6: Life event grouping completeness and per-group progress**
    - **Validates: Requirements 7.2, 7.4, 7.5**
  - [x] 3.4 Write property test for placeholder token replacement
    - **Property 7: Placeholder token replacement**
    - **Validates: Requirements 8.3**

- [x] 4. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Build the three new pages
  - [x] 5.1 Create `LifeStoryReflections` page at `FrontEndCode/src/pages/LifeStoryReflections.tsx`
    - Route: `/life-story-reflections`
    - Layout: `Header`, Back to Dashboard button (ghost, ArrowLeft icon → `/dashboard`), `OverallProgressSection`, extracted `ProgressSection`
    - Uses `useProgress` hook for category data, `getUserProgress` for overall progress
    - Handles auto-advance level logic (via ProgressSection)
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7_
  - [x] 5.2 Create `LifeEvents` page at `FrontEndCode/src/pages/LifeEvents.tsx`
    - Route: `/life-events`
    - Layout: `Header`, Back to Dashboard button, `OverallProgressSection`, list of `LifeEventGroup` cards
    - Uses `useLifeEventsProgress` hook for data
    - Empty state when no instanced questions assigned
    - Error state with retry on data fetch failure
    - Click on group/record button navigates to `RecordConversation` with question data
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 7.10_
  - [x] 5.3 Create `PersonalInsights` page at `FrontEndCode/src/pages/PersonalInsights.tsx`
    - Route: `/personal-insights`
    - Layout: `Header`, Back to Dashboard button, `OverallProgressSection`, "Coming Soon" card with description
    - No interactive question or survey content
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [x] 6. Redesign Dashboard as content hub and add routes
  - [x] 6.1 Redesign `Dashboard.tsx` as content hub
    - Keep: `Header`, `StreakCounter`, `DashboardInfoPanel`, survey overlay logic
    - Add: `OverallProgressSection` (using `getUserProgress`)
    - Add: Three `ContentPathCard` components replacing inline `ProgressSection`
      - Life Story Reflections card: uses `useProgress` to sum standard question progress, shows current level
      - Life Events card: uses `useLifeEventsProgress` for instanced question counts
      - Values & Emotions Deep Dive card: static "0 out of 0", disabled with "Coming Soon" badge
    - Remove: inline `ProgressSection` component (now imported from extracted file), "Continue Recording" button
    - Cards navigate via `useNavigate` to `/life-story-reflections`, `/life-events`, `/personal-insights`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 3.4, 4.1, 4.2, 4.3, 4.4, 4.5, 12.1, 12.2, 12.3, 12.4_
  - [x] 6.2 Add routes to `App.tsx`
    - Import `LifeStoryReflections`, `LifeEvents`, `PersonalInsights` pages
    - Add three `<Route>` entries wrapped in `<ProtectedRoute requiredPersona="legacy_maker">`
    - Routes: `/life-story-reflections`, `/life-events`, `/personal-insights`
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

- [x] 7. Progress calculation property tests
  - [x] 7.1 Write property test for Life Story progress calculation
    - **Property 1: Life Story progress calculation**
    - **Validates: Requirements 2.3, 12.1**
  - [x] 7.2 Write property test for Life Events total question calculation
    - **Property 2: Life Events total question calculation**
    - **Validates: Requirements 3.2, 12.2**
  - [x] 7.3 Write property test for overall progress excluding personal insights
    - **Property 3: Overall progress excludes personal insights**
    - **Validates: Requirements 4.4, 10.3**

- [x] 8. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document (Properties 1–7)
- Property 8 (progress consistency across pages) is an architectural property verified by the shared `getUserProgress` function — no separate test needed
- The backend change (task 1) and frontend type update should be deployed together
- IAM policy changes for `userQuestionStatusDB` Query and `allQuestionDB` BatchGetItem must be in the same deploy as the Lambda code change (per lambda-iam-permissions rule)
