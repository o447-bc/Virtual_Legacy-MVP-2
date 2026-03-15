"""
DynamoDB Table Creation Script for Virtual Legacy Application

This script creates a DynamoDB table called 'userQuestionStatusDB' that tracks
which questions each user has answered in the Virtual Legacy system. The table
uses a composite primary key to efficiently store and query user-question relationships.

Table Purpose:
- Store user responses to legacy questions
- Track completion status per user per question
- Enable efficient queries for user progress tracking

Key Design:
- Partition Key (userID): Groups all questions for a specific user
- Sort Key (questionID): Allows efficient querying of specific questions per user
- This composite key enables queries like "get all questions for user X" or 
  "check if user X answered question Y"
"""

import boto3

def create_table():
    """
    Creates the userQuestionStatusDB table in DynamoDB.
    
    Key Steps:
    1. Connect to DynamoDB service
    2. Delete existing table if present (for clean recreation)
    3. Create new table with composite primary key structure
    4. Wait for table to be fully provisioned
    """
    # Step 1: Initialize DynamoDB resource connection
    dynamodb = boto3.resource('dynamodb')
    
    # Step 2: Clean slate - remove existing table if it exists
    # This ensures we start fresh without schema conflicts
    try:
        table = dynamodb.Table('userQuestionStatusDB')
        table.delete()
        table.wait_until_not_exists()  # Wait for deletion to complete
        print("Deleted existing table")
    except:
        # Table doesn't exist - continue with creation
        pass
    
    # Step 3: Create new table with optimized structure
    table = dynamodb.create_table(
        TableName='userQuestionStatusDB',
        
        # Define composite primary key for efficient user-question lookups
        KeySchema=[
            {'AttributeName': 'userID', 'KeyType': 'HASH'},      # Partition key - distributes data
            {'AttributeName': 'questionID', 'KeyType': 'RANGE'}  # Sort key - enables range queries
        ],
        
        # Define attribute types for the key fields
        AttributeDefinitions=[
            {'AttributeName': 'userID', 'AttributeType': 'S'},     # String type
            {'AttributeName': 'questionID', 'AttributeType': 'S'}  # String type
        ],
        
        # Use pay-per-request billing for cost efficiency with variable workloads
        BillingMode='PAY_PER_REQUEST'
    )
    
    # Step 4: Wait for table to be fully created and ready for use
    table.wait_until_exists()
    print("✓ Created table with composite key")

if __name__ == "__main__":
    create_table()