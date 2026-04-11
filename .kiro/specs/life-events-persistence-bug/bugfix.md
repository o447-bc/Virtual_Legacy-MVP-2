# Bugfix Requirements Document

## Introduction

Life events survey data is lost after the second login session. Users complete the "Tell us about your life" survey, which correctly persists through the first logout/login cycle, but is destroyed on the second login. This causes the survey popup to reappear and the personalized life event questions (e.g., 18 divorce questions) to disappear.

The root cause is the `initializeUserProgress` Lambda function, which is called on every login. It performs an unconditional `put_item` on the `userStatusDB` table with only `{userId, currLevel, allowTranscription}`, overwriting the entire record including `hasCompletedSurvey`, `selectedLifeEvents`, `assignedQuestions`, and `lifeEventInstances`. The first login after survey completion reads the data before the async `initialize-progress` call destroys it; the second login reads the now-empty record.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a user who has completed the life events survey logs in THEN the `initializeUserProgress` Lambda overwrites the `userStatusDB` record with `put_item`, destroying `hasCompletedSurvey`, `selectedLifeEvents`, `assignedQuestions`, and `lifeEventInstances` fields

1.2 WHEN a user logs in a second time after the `initializeUserProgress` Lambda has already destroyed the survey data THEN `getSurveyStatus` returns `hasCompletedSurvey: false` and the survey popup reappears

1.3 WHEN the survey data is destroyed by the `put_item` overwrite THEN the user's personalized life event questions (e.g., 18 divorce questions) are no longer returned by the `/survey/status` endpoint

### Expected Behavior (Correct)

2.1 WHEN a user who has completed the life events survey logs in THEN the `initializeUserProgress` Lambda SHALL preserve all existing survey-related fields (`hasCompletedSurvey`, `selectedLifeEvents`, `assignedQuestions`, `lifeEventInstances`, `surveyCompletedAt`, `customLifeEvent`) in the `userStatusDB` record

2.2 WHEN a user logs in any number of times after completing the survey THEN `getSurveyStatus` SHALL return `hasCompletedSurvey: true` and the survey popup SHALL NOT reappear

2.3 WHEN a user logs in any number of times after completing the survey THEN the `/survey/status` endpoint SHALL continue to return the full `assignedQuestions` structure including all instanced question groups

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a new user who has never completed the survey logs in THEN the system SHALL CONTINUE TO initialize their `userStatusDB` record with `currLevel: 1` and `allowTranscription: true`

3.2 WHEN a user who has never completed the survey logs in THEN `getSurveyStatus` SHALL CONTINUE TO return `hasCompletedSurvey: false` and the survey popup SHALL appear

3.3 WHEN a user has existing progress records in `userQuestionLevelProgressDB` THEN the `initializeUserProgress` Lambda SHALL CONTINUE TO skip already-initialized question types

3.4 WHEN a user completes the survey for the first time THEN the survey submission Lambda SHALL CONTINUE TO write the full survey data to `userStatusDB` without interference from `initializeUserProgress`
