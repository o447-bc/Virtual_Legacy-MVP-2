# Question Database Functions

This directory contains AWS Lambda functions for interacting with the question database for the Virtual Legacy application. These functions provide various capabilities for retrieving question types, counting valid questions, and managing user question interactions.

## Function Summary

- **getNumQuestionTypes**: Retrieves the count of unique question types in the database.
- **getNumValidQuestionsForQType**: Returns the count of valid questions for a specific question type.
- **getQuestionTypeData**: Retrieves comprehensive data about all question types including friendly names and valid question counts.
- **getQuestionTypes**: Returns a list of all unique question types in the database.
- **getUnansweredQuestionsFromUser**: Retrieves question IDs that a specific user has not yet answered for a given question type.

## Detailed Function Documentation

### getNumQuestionTypes

**Purpose**: Counts and returns the number of unique question types in the database.

**Input Arguments**: 
- None required

**Output**:
- `uniqueQuestionTypesCount`: Number of unique question types
- `questionTypes`: List of all unique question types

### getNumValidQuestionsForQType

**Purpose**: Counts the number of valid questions for a specific question type.

**Input Arguments**:
- `questionType`: The type of questions to count (required)
  - Can be provided in `queryStringParameters` or directly in the event body

**Output**:
- `validQuestionCount`: Number of valid questions for the specified question type

### getQuestionTypeData

**Purpose**: Retrieves comprehensive data about all question types including their friendly names and the count of valid questions for each type.

**Input Arguments**:
- None required

**Output**:
- `uniqueQuestionTypesCount`: Number of unique question types
- `questionTypes`: List of all unique question types
- `friendlyNames`: List of friendly names corresponding to each question type
- `numValidQuestions`: List of counts of valid questions for each question type

### getQuestionTypes

**Purpose**: Returns a list of all unique question types in the database.

**Input Arguments**:
- None required

**Output**:
- `questionTypes`: List of all unique question types

### getUnansweredQuestionsFromUser

**Purpose**: Retrieves question IDs that a specific user has not yet answered for a given question type.

**Input Arguments**:
- `questionType`: The type of questions to retrieve (required)
- `userId`: The ID of the user (required)
  - Both can be provided in `queryStringParameters` or directly in the event body

**Output**:
- `unansweredQuestionIds`: List of question IDs that are valid and not yet answered by the user

## Database Schema

These functions interact with two DynamoDB tables:

1. **allQuestionDB**: Stores all questions with attributes:
   - `questionId`: Unique identifier for the question
   - `questionType`: Category of the question
   - `Question`: The actual question text
   - `Valid`: Flag indicating if the question is valid (1) or not (0)

2. **userQuestionStatusDB**: Tracks which questions users have answered:
   - `userId`: Identifier for the user
   - `questionId`: Identifier for the question
   - `questionType`: Category of the question

## Usage Examples

The test files in each function directory demonstrate how to call these functions:

- Use `getQuestionTypes` to retrieve all available question categories
- Use `getNumValidQuestionsForQType` to determine how many valid questions exist for a specific category
- Use `getUnansweredQuestionsFromUser` to find which questions a user still needs to answer
- Use `getQuestionTypeData` to get comprehensive information about all question types