# Requirements Document

## Introduction

The SoulReel Dashboard currently serves as a single flat view showing a streak counter, info panel, overall progress bar, and a grid of per-category (theme) progress bars that link directly to the recording flow. All questions — standard life-story questions and life-event-specific instanced questions — are mixed together in this single view.

This feature redesigns the Dashboard into a content hub that branches into three distinct content paths: Life Story Reflections (the existing standard questions organized by theme/level), Life Events (the recently added life-event-specific instanced questions from the survey feature), and Personal Insight Reflections (a future placeholder for emotional/psychology-based evaluations). The Dashboard retains the overall progress display at the top but replaces the per-category progress grid with three large, mobile-friendly navigation cards. Each card navigates to a dedicated page showing the overall progress bar plus path-specific content.

## Glossary

- **Content_Hub**: The redesigned Dashboard page that displays overall progress and three navigation cards for the three content paths, replacing the current per-category progress grid.
- **Content_Path_Card**: A large, interactive card on the Content_Hub that represents one of the three content paths, displaying the path title, progress summary, and navigating to the path's dedicated page on click.
- **Life_Story_Reflections_Page**: The dedicated page for the "Life Story Reflections" content path, displaying the per-category (theme) progress bars and click-to-record functionality that currently exists on the Dashboard.
- **Life_Events_Page**: The dedicated page for the "Life Events" content path, displaying life-event-specific questions grouped by life event, ordered by lowest level first then alphabetical, with all questions available regardless of the user's current level.
- **Personal_Insight_Page**: The dedicated placeholder page for the "Values & Emotions Deep Dive" content path, displaying a "Coming Soon" state with no functional content.
- **Overall_Progress_Bar**: The existing progress bar component showing the user's total completed questions out of total assigned questions, displayed as a constant element on the Content_Hub and on each dedicated content path page.
- **Legacy_Maker**: A user with `persona_type` of `legacy_maker` who creates video responses to questions.
- **assignedQuestions**: The structured object in `userStatusDB` containing `standard` (flat list of questionIds) and `instanced` (array of instance groups with `eventKey`, `instanceName`, `instanceOrdinal`, `questionIds`).
- **lifeEventInstances**: The array in `userStatusDB` containing instance data for repeatable life events, each with `eventKey` and `instances` array.
- **getProgressSummary2**: The existing Lambda that returns per-category progress data including `progressItems`, `questionTypes`, `friendlyNames`, `numValidQuestions`, and unanswered question maps.
- **useProgress**: The existing React Query hook that fetches progress data from getProgressSummary2 and processes it into `ProgressData` for display.

## Requirements

### Requirement 1: Content Hub Dashboard Layout

**User Story:** As a legacy maker, I want the Dashboard to show three clear content paths, so that I can choose which type of reflection to work on.

#### Acceptance Criteria

1. THE Content_Hub SHALL display the StreakCounter component and DashboardInfoPanel at the top of the page, preserving the current layout order.
2. THE Content_Hub SHALL display the Overall_Progress_Bar below the info panel as a constant element visible before the content path cards.
3. THE Content_Hub SHALL display three Content_Path_Cards below the Overall_Progress_Bar, replacing the current per-category progress grid.
4. THE Content_Hub SHALL arrange the three Content_Path_Cards in a single-column vertical stack on mobile viewports (below 640px) and in a responsive grid on larger viewports.
5. THE Content_Hub SHALL preserve the existing Life Events Survey overlay behavior, rendering the survey overlay when `hasCompletedSurvey` is `false` and the retake overlay when triggered via URL parameter.

### Requirement 2: Life Story Reflections Card

**User Story:** As a legacy maker, I want to see my Life Story Reflections progress at a glance on the Dashboard, so that I can quickly navigate to continue recording standard questions.

#### Acceptance Criteria

1. THE Content_Hub SHALL display a Content_Path_Card titled "Life Story Reflections" with a subtitle "General Questions" or equivalent descriptor.
2. THE "Life Story Reflections" Content_Path_Card SHALL display the user's current level (e.g., "Level X").
3. THE "Life Story Reflections" Content_Path_Card SHALL display the number of completed standard questions out of total standard questions (e.g., "X out of Y questions").
4. WHEN the user clicks the "Life Story Reflections" Content_Path_Card, THE Content_Hub SHALL navigate to the Life_Story_Reflections_Page at route `/life-story-reflections`.

### Requirement 3: Life Events Card

**User Story:** As a legacy maker, I want to see my Life Events progress at a glance on the Dashboard, so that I can navigate to answer life-event-specific questions.

#### Acceptance Criteria

1. THE Content_Hub SHALL display a Content_Path_Card titled "Life Events".
2. THE "Life Events" Content_Path_Card SHALL display the number of completed life event questions out of total life event questions across all instance groups (e.g., "X out of Y questions completed"). Each instance group (e.g., each spouse, each child) is counted separately — if a user has 2 spouses with 3 questions each, the total is 6.
3. WHEN the user clicks the "Life Events" Content_Path_Card, THE Content_Hub SHALL navigate to the Life_Events_Page at route `/life-events`.
4. WHEN the user has no assigned instanced questions (empty `assignedQuestions.instanced`), THE "Life Events" Content_Path_Card SHALL display "0 out of 0 events completed" or an equivalent empty-state message.

### Requirement 4: Personal Insight Reflections Card

**User Story:** As a legacy maker, I want to see a placeholder for future Values & Emotions content, so that I know more content is coming.

#### Acceptance Criteria

1. THE Content_Hub SHALL display a Content_Path_Card with the display title "Values & Emotions Deep Dive".
2. THE "Values & Emotions Deep Dive" Content_Path_Card SHALL display a "Coming Soon" indicator or equivalent placeholder text.
3. THE "Values & Emotions Deep Dive" Content_Path_Card SHALL display "0 out of 0 surveys done" or equivalent placeholder progress.
4. THE "Values & Emotions Deep Dive" Content_Path_Card SHALL NOT contribute to the Overall_Progress_Bar question count.
5. WHEN the user clicks the "Values & Emotions Deep Dive" Content_Path_Card, THE Content_Hub SHALL navigate to the Personal_Insight_Page at route `/personal-insights`.

### Requirement 5: Content Path Card Visual Design

**User Story:** As a legacy maker, I want the content path cards to be visually attractive and easy to tap on mobile, so that navigation feels intuitive and pleasant.

#### Acceptance Criteria

1. THE Content_Path_Card component SHALL render as a large, visually prominent card with a minimum touch target of 48px height on mobile viewports.
2. THE Content_Path_Card component SHALL use the existing SoulReel design system (Tailwind classes, `legacy-purple` and `legacy-navy` color tokens, shadcn/ui components).
3. THE Content_Path_Card component SHALL display a visual hover state on desktop (e.g., shadow elevation change, border color change) and a press/active state on mobile.
4. THE Content_Path_Card component SHALL include a visual indicator (e.g., chevron icon, arrow) signaling that the card is navigable.
5. THE Content_Path_Card component SHALL be keyboard accessible, responding to Enter and Space key presses for navigation, with a visible focus ring.
6. EACH Content_Path_Card SHALL have a distinct visual accent or icon to differentiate the three content paths from each other.

### Requirement 6: Life Story Reflections Page

**User Story:** As a legacy maker, I want a dedicated page for Life Story Reflections that shows my per-category progress and lets me record, so that I can focus on standard questions without distraction.

#### Acceptance Criteria

1. THE Life_Story_Reflections_Page SHALL display the Overall_Progress_Bar at the top of the page content area, below the Header.
2. THE Life_Story_Reflections_Page SHALL display the per-category progress grid with the same layout, data, and click-to-record behavior currently present on the Dashboard's ProgressSection component.
3. THE Life_Story_Reflections_Page SHALL NOT display a "Continue Recording" button; users navigate directly by clicking individual category progress bars.
4. THE Life_Story_Reflections_Page SHALL display a "Back to Dashboard" navigation element that returns the user to the Content_Hub.
5. THE Life_Story_Reflections_Page SHALL use the existing `useProgress` hook to fetch progress data from getProgressSummary2.
6. THE Life_Story_Reflections_Page SHALL handle the auto-advance level logic when all categories at the current level are complete, matching the current Dashboard behavior.
7. THE Life_Story_Reflections_Page SHALL be accessible at the route `/life-story-reflections` and protected by the existing `ProtectedRoute` component with `requiredPersona="legacy_maker"`.

### Requirement 7: Life Events Page

**User Story:** As a legacy maker, I want a dedicated page showing my life-event-specific questions grouped by life event, so that I can answer personalized questions about my specific life experiences.

#### Acceptance Criteria

1. THE Life_Events_Page SHALL display the Overall_Progress_Bar at the top of the page content area, below the Header.
2. THE Life_Events_Page SHALL display life event questions grouped by life event instance (e.g., all questions about "Sarah" under a "got_married — Sarah" heading).
3. THE Life_Events_Page SHALL order life event groups by lowest question difficulty level first, then alphabetically by event key within the same level.
4. THE Life_Events_Page SHALL display all assigned life event questions regardless of the user's current level (life event questions are NOT gated to levels).
5. THE Life_Events_Page SHALL display progress per life event group showing completed questions out of total questions for that group.
6. WHEN the user clicks a life event group or a record button within a group, THE Life_Events_Page SHALL navigate to the recording flow (RecordConversation) with the appropriate question data for that life event group.
7. THE Life_Events_Page SHALL display a "Back to Dashboard" navigation element that returns the user to the Content_Hub.
8. THE Life_Events_Page SHALL be accessible at the route `/life-events` and protected by the existing `ProtectedRoute` component with `requiredPersona="legacy_maker"`.
9. WHEN the user has no assigned instanced questions, THE Life_Events_Page SHALL display an empty state message (e.g., "No life event questions assigned. Complete the Life Events Survey to get personalized questions.").
10. THE Life_Events_Page SHALL fetch the user's `assignedQuestions.instanced` data and answered status to calculate per-group progress.

### Requirement 8: Life Events Question Data Retrieval

**User Story:** As a frontend developer, I want to retrieve life event question data with answered status, so that the Life Events Page can display accurate progress per life event group.

#### Acceptance Criteria

1. THE Life_Events_Page SHALL retrieve the user's `assignedQuestions` structure from the survey status endpoint or from the progress data.
2. THE Life_Events_Page SHALL retrieve the answered status for each life event question to calculate per-group completion counts.
3. THE Life_Events_Page SHALL retrieve the question text for each life event question, replacing `instancePlaceholder` tokens with the corresponding `instanceName` from the instance group.
4. IF the data retrieval fails, THEN THE Life_Events_Page SHALL display an error message with a retry option.

### Requirement 9: Personal Insight Reflections Page

**User Story:** As a legacy maker, I want a placeholder page for the future Values & Emotions Deep Dive, so that I can see what is coming next.

#### Acceptance Criteria

1. THE Personal_Insight_Page SHALL display the Overall_Progress_Bar at the top of the page content area, below the Header.
2. THE Personal_Insight_Page SHALL display a "Coming Soon" message with a brief description of the future feature (e.g., "Emotional and psychology-based evaluations are coming in a future update.").
3. THE Personal_Insight_Page SHALL display a "Back to Dashboard" navigation element that returns the user to the Content_Hub.
4. THE Personal_Insight_Page SHALL be accessible at the route `/personal-insights` and protected by the existing `ProtectedRoute` component with `requiredPersona="legacy_maker"`.
5. THE Personal_Insight_Page SHALL NOT display any interactive question or survey content.

### Requirement 10: Overall Progress Bar Consistency

**User Story:** As a legacy maker, I want to see my overall progress on every content page, so that I always know how far along I am in my legacy journey.

#### Acceptance Criteria

1. THE Overall_Progress_Bar SHALL appear on the Content_Hub, the Life_Story_Reflections_Page, the Life_Events_Page, and the Personal_Insight_Page.
2. THE Overall_Progress_Bar SHALL display the same completed count and total count across all pages for the same user session.
3. THE Overall_Progress_Bar SHALL calculate total question count from `assignedQuestions.standard` length plus total instanced question count, excluding Personal Insight Reflections (which contribute zero).
4. THE Overall_Progress_Bar SHALL use the existing `ProgressBar` component and `getUserProgress` service function.

### Requirement 11: Routing and Navigation

**User Story:** As a frontend developer, I want clean routes for each content path page, so that users can navigate directly and the browser back button works correctly.

#### Acceptance Criteria

1. THE application SHALL register the following new routes: `/life-story-reflections`, `/life-events`, `/personal-insights`.
2. EACH new route SHALL be wrapped in the existing `ProtectedRoute` component with `requiredPersona="legacy_maker"`.
3. WHEN the user navigates from a content path page back to the Content_Hub using the "Back to Dashboard" element, THE application SHALL navigate to `/dashboard`.
4. WHEN the user uses the browser back button from a content path page, THE application SHALL return to the Content_Hub.
5. WHEN a Legacy_Maker with `hasCompletedSurvey` equal to `false` navigates to any of the new routes, THE existing Survey_Gate logic SHALL redirect the user to the Dashboard where the survey overlay is displayed.

### Requirement 12: Content Path Progress Calculation

**User Story:** As a legacy maker, I want accurate progress numbers on each content path card, so that I can see how much I have completed in each area.

#### Acceptance Criteria

1. THE "Life Story Reflections" Content_Path_Card SHALL calculate its progress from the standard (non-instanced) questions in the user's assigned set, using the existing per-category progress data from `useProgress`.
2. THE "Life Events" Content_Path_Card SHALL calculate its progress from the instanced questions in the user's assigned set, counting each instanced question copy as a separate item.
3. THE "Values & Emotions Deep Dive" Content_Path_Card SHALL display static placeholder progress (0 out of 0) with no backend calculation.
4. WHEN the user completes a question and returns to the Content_Hub, THE Content_Path_Cards SHALL reflect the updated progress counts.
