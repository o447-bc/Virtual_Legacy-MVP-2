#!/usr/bin/env python3
"""
Virtual Legacy User Data Reset Utility

This utility safely deletes all user data from the Virtual Legacy system while
preserving the Cognito user account. This allows testing first-time login scenarios.

Data Deleted:
  S3 (virtual-legacy bucket):
    - user-responses/{userId}/   — Video responses, thumbnails, transcripts
    - conversations/{userId}/    — Conversation audio and transcripts
    - psych-exports/{userId}/    — Psychological test export files (PDF/CSV)

  S3 (soulreel-exports-temp-{accountId} bucket):
    - exports/{userId}/          — Data export ZIP archives (GDPR/content packages)

  DynamoDB tables (14 tables):
    - userQuestionStatusDB           — Answered questions tracking (userId + questionId)
    - userQuestionLevelProgressDB    — Level progress per question type (userId + questionType)
    - userStatusDB                   — Current global level (userId)
    - PersonaRelationshipsDB         — User relationships as initiator or benefactor
    - AccessConditionsDB             — Access conditions tied to relationships (cascade delete)
    - PersonaSignupTempDB            — Temporary signup / invitation data
    - EngagementDB                   — Streak and engagement tracking (userId)
    - WebSocketConnectionsDB         — Active WebSocket connections (scan by userId)
    - ConversationStateDB            — In-flight conversation state (scan by userId)
    - UserSubscriptionsDB            — Stripe subscription and billing tier (userId)
    - DataRetentionDB                — Export requests, deletion requests, dormancy (userId + recordType)
    - UserTestProgressDB             — In-progress psych test responses (userId + testId)
    - UserTestResultsDB              — Completed psych test results/scores (userId + testIdVersionTimestamp)
    - FeedbackReportsDB              — User-submitted bug reports and feature requests (scan by userId)

Data Preserved:
  - Cognito User Pool account (email, password, authentication)

⚠️  DATA RETENTION WARNING:
  - If the user has pending data export requests (DataRetentionDB), those records will be deleted.
  - If the user has a pending account deletion request (grace period), that will also be cleared.
  - Any exported ZIP archives in the exports temp bucket will be removed immediately.
  - Psych test results are permanently deleted — there is no undo.

CAUTION: This script permanently deletes user data. Use for testing only.

Author: Kiro AI Assistant
Date: 2026-02-21
Updated: 2026-04-26 — Added 7 new tables (UserSubscriptionsDB, DataRetentionDB,
    UserTestProgressDB, UserTestResultsDB, ConversationStateDB, AccessConditionsDB,
    FeedbackReportsDB), 2 new S3 prefixes (psych-exports, exports temp bucket),
    cascade delete of AccessConditionsDB from PersonaRelationships, and data
    retention warning.
"""

import boto3
import json
import sys
import argparse
from typing import Optional, List, Dict, Any
from botocore.exceptions import ClientError, NoCredentialsError
from boto3.dynamodb.conditions import Key, Attr


class VirtualLegacyUserDataReset:
    """
    User data reset utility for Virtual Legacy system.
    
    This class handles the complete removal of user data across all AWS services
    while preserving the Cognito user account for testing purposes.
    
    Key Features:
    - Deletes all S3 files (videos, audio, transcripts, psych exports, data exports)
    - Deletes all DynamoDB records (progress, status, relationships, subscriptions,
      psych tests, feedback, data retention, conversation state, access conditions)
    - Cascade-deletes AccessConditionsDB records when deleting PersonaRelationships
    - Preserves Cognito user account
    - Supports dry-run mode for safe testing
    - Single confirmation for all operations (no per-step prompts)
    - Prints data retention warning before confirmation
    """
    
    def __init__(self, dry_run: bool = False):
        """
        Initialize AWS clients and configuration.
        
        Sets up connections to Cognito, S3, DynamoDB, and STS services.
        Configures table names, bucket information, and discovers the AWS account ID
        (needed for the exports temp bucket name which includes the account ID).
        
        Args:
            dry_run (bool): If True, show what would be deleted without actually deleting
        """
        try:
            # AWS service clients - all in us-east-1 region
            self.cognito_client = boto3.client('cognito-idp', region_name='us-east-1')
            self.s3_client = boto3.client('s3', region_name='us-east-1')
            self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
            
            # Discover the AWS account ID via STS so we can construct the exports
            # temp bucket name (soulreel-exports-temp-{accountId}). This avoids
            # hardcoding the account ID which would break across environments.
            sts_client = boto3.client('sts', region_name='us-east-1')
            self.aws_account_id = sts_client.get_caller_identity()['Account']
            
            # Configuration from SAM template
            self.user_pool_id = 'us-east-1_KsG65yYlo'  # Virtual Legacy Cognito User Pool
            self.s3_bucket = 'virtual-legacy'  # Main S3 bucket for all user data
            
            # Exports temp bucket — name includes account ID per SAM template:
            #   BucketName: !Sub soulreel-exports-temp-${AWS::AccountId}
            # This bucket has a 7-day lifecycle rule, but we clean up immediately
            # so the test account reset is thorough.
            self.exports_temp_bucket = f'soulreel-exports-temp-{self.aws_account_id}'
            
            # ---------------------------------------------------------------
            # DynamoDB table names — ALL tables that contain user-specific data.
            #
            # IMPORTANT: When a new DynamoDB table is added to template.yml that
            # stores user data (keyed by userId or containing userId as an attribute),
            # it MUST be added here and a corresponding deletion step added to
            # run_reset(). Otherwise test account resets will leave orphaned data.
            #
            # Tables NOT included (not user-specific):
            #   - PsychTestsDB        — Test metadata/definitions, not user data
            #   - SystemSettingsDB     — Admin configuration key-value store
            #   - EmailCaptureDB       — Pre-signup marketing captures, keyed by email
            #   - EmailCaptureRateLimitDB — IP-based rate limiting with TTL
            #   - allQuestionDB        — Question content, not user data
            # ---------------------------------------------------------------
            self.tables = {
                # === ORIGINAL TABLES (present since utility was first written 2026-02-21) ===
                'userQuestionStatusDB': 'userQuestionStatusDB',              # Answered questions tracking (PK: userId, SK: questionId)
                'userQuestionLevelProgressDB': 'userQuestionLevelProgressDB', # Level progress per question type (PK: userId, SK: questionType)
                'userStatusDB': 'userStatusDB',                              # Current global level (PK: userId)
                'PersonaRelationshipsDB': 'PersonaRelationshipsDB',          # User relationships (PK: initiator_id, SK: related_user_id)
                'PersonaSignupTempDB': 'PersonaSignupTempDB',                # Temporary signup data (PK: userName)
                'EngagementDB': 'EngagementDB',                              # Streak and engagement tracking (PK: userId)
                'WebSocketConnectionsDB': 'WebSocketConnectionsDB',          # Active WebSocket connections (PK: connectionId, scan by userId)
                
                # === TABLES ADDED 2026-04-26 — these were created after the utility was first written ===
                'AccessConditionsDB': 'AccessConditionsDB',                  # Access conditions for relationships (PK: relationship_key, SK: condition_id)
                'ConversationStateDB': 'ConversationStateDB',                # In-flight conversation state (PK: connectionId, scan by userId)
                'UserSubscriptionsDB': 'UserSubscriptionsDB',                # Stripe subscription/billing tier (PK: userId)
                'DataRetentionDB': 'DataRetentionDB',                        # Export requests, deletion requests, dormancy (PK: userId, SK: recordType)
                'UserTestProgressDB': 'UserTestProgressDB',                  # In-progress psych test responses with TTL (PK: userId, SK: testId)
                'UserTestResultsDB': 'UserTestResultsDB',                    # Completed psych test results/scores (PK: userId, SK: testIdVersionTimestamp)
                'FeedbackReportsDB': 'FeedbackReportsDB',                    # Bug reports and feature requests (PK: reportId, scan by userId)
            }
            
            # Dry run mode - if True, only show what would be deleted
            self.dry_run = dry_run
            
            # User has confirmed - skip individual operation confirmations after final RESET
            # This flag is set to True after user types 'RESET' in final confirmation
            self.confirmed = False
            
            # Summary of actions taken - used for final report
            self.actions_taken = []
            
            if dry_run:
                print("🔍 DRY RUN MODE: No data will be actually deleted")
            print("✅ AWS clients initialized successfully")
            print(f"   AWS Account ID: {self.aws_account_id}")
            print(f"   Exports temp bucket: {self.exports_temp_bucket}")
            
        except NoCredentialsError:
            print("❌ ERROR: AWS credentials not found. Please configure AWS CLI.")
            sys.exit(1)
        except Exception as e:
            print(f"❌ ERROR: Failed to initialize AWS clients: {str(e)}")
            sys.exit(1)
    
    def get_user_email(self) -> str:
        """
        Prompt user for email address with validation.
        
        Validates email format and requires confirmation before proceeding.
        Converts email to lowercase for consistency.
        
        Returns:
            str: Validated email address in lowercase
        """
        while True:
            email = input("\n📧 Enter the email address of the user to reset: ").strip()
            
            if not email:
                print("❌ Email address cannot be empty. Please try again.")
                continue
                
            # Basic email validation - must have @ and domain with .
            if '@' not in email or '.' not in email.split('@')[1]:
                print("❌ Invalid email format. Please enter a valid email address.")
                continue
                
            # Convert to lowercase for consistency with Cognito
            email = email.lower()
            
            # Confirm email address to prevent typos
            confirm = input(f"\n⚠️  CONFIRM: You want to reset data for user '{email}'? (yes/no): ").strip().lower()
            if confirm in ['yes', 'y']:
                return email
            elif confirm in ['no', 'n']:
                print("Operation cancelled by user.")
                sys.exit(0)
            else:
                print("Please enter 'yes' or 'no'.")
    
    def find_cognito_user(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Find user in Cognito User Pool by email address.
        
        Searches through all users in the User Pool to find matching email.
        Uses pagination to handle large user pools.
        
        Args:
            email (str): Email address to search for
            
        Returns:
            Optional[Dict]: User data if found (includes Username, Attributes, UserStatus), None otherwise
        """
        try:
            print(f"\n🔍 Searching for user '{email}' in Cognito User Pool...")
            
            # List all users and find by email - uses pagination for large user pools
            paginator = self.cognito_client.get_paginator('list_users')
            
            for page in paginator.paginate(UserPoolId=self.user_pool_id):
                for user in page['Users']:
                    # Check email attribute - Cognito stores email in Attributes array
                    for attr in user.get('Attributes', []):
                        if attr['Name'] == 'email' and attr['Value'].lower() == email:
                            print(f"✅ Found user: {user['Username']} ({email})")
                            return user
            
            print(f"❌ User '{email}' not found in Cognito User Pool")
            return None
            
        except ClientError as e:
            print(f"❌ ERROR: Failed to search Cognito users: {e}")
            return None
    
    def confirm_action(self, action_description: str) -> bool:
        """
        Get user confirmation before performing destructive action.
        Once user has confirmed the final RESET prompt, this always returns True.
        
        This method is called before each major operation. After the user types 'RESET'
        in the final confirmation, self.confirmed is set to True and this method
        will automatically approve all subsequent operations without prompting.
        
        Args:
            action_description (str): Description of the action to be performed
            
        Returns:
            bool: True if user has confirmed or already confirmed globally, False if cancelled
        """
        if self.confirmed:
            # User already confirmed with RESET - proceed without asking
            # Just show what we're doing with a simple arrow indicator
            print(f"   ▶ {action_description}")
            return True
            
        if self.dry_run:
            # In dry run mode, show what would be done but don't actually do it
            print(f"\n[DRY RUN] Would perform: {action_description}")
            return True
            
        # Ask for confirmation for this specific operation
        print(f"\n🚨 ABOUT TO PERFORM: {action_description}")
        while True:
            response = input("Continue? (Y/N): ").strip().upper()
            if response == 'Y':
                return True
            elif response == 'N':
                print("❌ Action cancelled by user")
                return False
            else:
                print("Please enter 'Y' for Yes or 'N' for No")

    
    # ===================================================================
    # S3 DELETION METHODS
    # ===================================================================
    
    def delete_s3_files(self, user_id: str, prefix: str, description: str,
                        bucket: Optional[str] = None) -> bool:
        """
        Delete all S3 files for the specified prefix from a given bucket.
        
        Uses pagination to handle large numbers of files.
        Deletes in batches of 1000 (S3 API limit per delete_objects call).
        
        Args:
            user_id (str): Cognito user ID (used in confirmation message)
            prefix (str): S3 prefix to delete (e.g., "user-responses/{userId}/")
            description (str): Human-readable description for logging (e.g., "user-responses")
            bucket (str): S3 bucket name. Defaults to self.s3_bucket (virtual-legacy)
                          if not specified. Pass self.exports_temp_bucket for export ZIPs.
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Default to the main virtual-legacy bucket if no bucket specified
        target_bucket = bucket or self.s3_bucket
        
        action_desc = f"Delete all S3 files from s3://{target_bucket}/{prefix}"
        if not self.confirm_action(action_desc):
            return False
            
        try:
            print(f"\n🗑️  Deleting S3 files from s3://{target_bucket}/{prefix}...")
            
            # List objects with prefix (with pagination support for large datasets)
            paginator = self.s3_client.get_paginator('list_objects_v2')
            
            all_objects = []
            for page in paginator.paginate(Bucket=target_bucket, Prefix=prefix):
                if 'Contents' in page:
                    all_objects.extend(page['Contents'])
            
            if not all_objects:
                print(f"ℹ️  No S3 files found at s3://{target_bucket}/{prefix}")
                self.actions_taken.append(f"S3 {description}: No files found")
                return True
            
            if self.dry_run:
                print(f"[DRY RUN] Would delete {len(all_objects)} files from s3://{target_bucket}/{prefix}")
                self.actions_taken.append(f"S3 {description}: Would delete {len(all_objects)} files")
                return True
            
            # Delete objects in batches (S3 delete_objects supports max 1000 objects per call)
            total_deleted = 0
            batch_size = 1000
            
            for i in range(0, len(all_objects), batch_size):
                batch = all_objects[i:i + batch_size]
                objects_to_delete = [{'Key': obj['Key']} for obj in batch]
                
                delete_response = self.s3_client.delete_objects(
                    Bucket=target_bucket,
                    Delete={'Objects': objects_to_delete}
                )
                
                batch_deleted = len(delete_response.get('Deleted', []))
                total_deleted += batch_deleted
                print(f"   Deleted batch: {batch_deleted} files")
            
            print(f"✅ Successfully deleted {total_deleted} S3 files total")
            self.actions_taken.append(f"S3 {description}: Deleted {total_deleted} files")
            
            return True
            
        except ClientError as e:
            print(f"❌ ERROR: Failed to delete S3 files from s3://{target_bucket}/{prefix}: {e}")
            return False

    
    # ===================================================================
    # DYNAMODB DELETION METHODS — Generic helpers
    # ===================================================================
    
    def delete_dynamodb_table_by_partition_key(self, table_name: str, key_name: str, 
                                                key_value: str, sort_key_name: Optional[str] = None) -> bool:
        """
        Delete all records from a DynamoDB table by partition key.
        
        Queries the table for all records matching the partition key,
        then deletes each record individually. Handles pagination for large datasets.
        
        This is the workhorse method for tables where userId IS the partition key.
        For tables where userId is stored as a non-key attribute, use
        delete_dynamodb_by_scan() instead.
        
        Args:
            table_name (str): Name of the DynamoDB table
            key_name (str): Partition key attribute name (e.g., 'userId')
            key_value (str): Partition key value to query (e.g., user's Cognito ID)
            sort_key_name (str): Sort key attribute name if table has composite key (e.g., 'questionId')
            
        Returns:
            bool: True if successful, False otherwise
        """
        action_desc = f"Delete all records from {table_name} for {key_name}={key_value}"
        if not self.confirm_action(action_desc):
            return False
            
        try:
            print(f"\n🗑️  Deleting records from {table_name}...")
            table = self.dynamodb.Table(table_name)
            
            # Query all records for this key - more efficient than scan
            response = table.query(
                KeyConditionExpression=Key(key_name).eq(key_value)
            )
            
            items = response['Items']
            
            # Handle pagination - DynamoDB returns max 1MB per query
            while 'LastEvaluatedKey' in response:
                response = table.query(
                    KeyConditionExpression=Key(key_name).eq(key_value),
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                items.extend(response['Items'])
            
            if not items:
                print(f"ℹ️  No records found in {table_name}")
                self.actions_taken.append(f"{table_name}: No records found")
                return True
            
            if self.dry_run:
                print(f"[DRY RUN] Would delete {len(items)} records from {table_name}")
                self.actions_taken.append(f"{table_name}: Would delete {len(items)} records")
                return True
            
            # Delete each record - DynamoDB requires individual delete operations
            deleted_count = 0
            for item in items:
                if sort_key_name:
                    # Composite key (partition + sort)
                    table.delete_item(
                        Key={
                            key_name: item[key_name],
                            sort_key_name: item[sort_key_name]
                        }
                    )
                else:
                    # Simple partition key only
                    table.delete_item(Key={key_name: item[key_name]})
                deleted_count += 1
            
            print(f"✅ Successfully deleted {deleted_count} records from {table_name}")
            self.actions_taken.append(f"{table_name}: Deleted {deleted_count} records")
            return True
            
        except ClientError as e:
            print(f"❌ ERROR: Failed to delete from {table_name}: {e}")
            return False
    
    def delete_dynamodb_single_item(self, table_name: str, key: Dict[str, str]) -> bool:
        """
        Delete a single item from DynamoDB table.
        
        Used for tables where user has only one record (e.g., userStatusDB, EngagementDB,
        UserSubscriptionsDB).
        
        Args:
            table_name (str): Name of the DynamoDB table
            key (dict): Primary key of the item to delete (e.g., {'userId': 'abc-123'})
            
        Returns:
            bool: True if successful, False otherwise
        """
        action_desc = f"Delete record from {table_name} with key {key}"
        if not self.confirm_action(action_desc):
            return False
            
        try:
            print(f"\n🗑️  Deleting record from {table_name}...")
            table = self.dynamodb.Table(table_name)
            
            if self.dry_run:
                print(f"[DRY RUN] Would delete record from {table_name}")
                self.actions_taken.append(f"{table_name}: Would delete 1 record")
                return True
            
            # Delete with ReturnValues to check if item existed
            response = table.delete_item(
                Key=key,
                ReturnValues='ALL_OLD'
            )
            
            if 'Attributes' in response:
                print(f"✅ Successfully deleted record from {table_name}")
                self.actions_taken.append(f"{table_name}: Deleted 1 record")
            else:
                print(f"ℹ️  No record found in {table_name}")
                self.actions_taken.append(f"{table_name}: No record found")
            
            return True
            
        except ClientError as e:
            print(f"❌ ERROR: Failed to delete from {table_name}: {e}")
            return False

    def delete_dynamodb_by_scan(self, table_name: str, filter_attr: str,
                                 filter_value: str, pk_attr: str,
                                 description: str) -> bool:
        """
        Delete all records from a DynamoDB table by scanning for a non-key attribute.
        
        Used for tables where userId is NOT the partition key but is stored as a
        regular attribute. Examples:
          - WebSocketConnectionsDB (PK: connectionId, has userId attribute)
          - ConversationStateDB    (PK: connectionId, has userId attribute)
          - FeedbackReportsDB      (PK: reportId, has userId attribute)
        
        This is less efficient than a query (full table scan) but necessary when
        there's no GSI on the attribute we need to filter by.
        
        Args:
            table_name (str): Name of the DynamoDB table
            filter_attr (str): Attribute name to filter on (e.g., 'userId')
            filter_value (str): Value to match (e.g., the user's Cognito ID)
            pk_attr (str): Partition key attribute name for deletion (e.g., 'connectionId')
            description (str): Human-readable description for logging
            
        Returns:
            bool: True if successful, False otherwise
        """
        action_desc = f"Delete {description} from {table_name} where {filter_attr}={filter_value}"
        
        if not self.confirm_action(action_desc):
            return False
            
        try:
            print(f"\n🗑️  Scanning {table_name} for {filter_attr}={filter_value}...")
            table = self.dynamodb.Table(table_name)
            
            # Scan table with filter — can't query because the filter attribute is not a key
            response = table.scan(
                FilterExpression=Attr(filter_attr).eq(filter_value)
            )
            
            items = response['Items']
            
            # Handle pagination for scan — DynamoDB returns max 1MB per scan
            while 'LastEvaluatedKey' in response:
                response = table.scan(
                    FilterExpression=Attr(filter_attr).eq(filter_value),
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                items.extend(response['Items'])
            
            if not items:
                print(f"ℹ️  No {description} found in {table_name}")
                self.actions_taken.append(f"{table_name}: No {description} found")
                return True
            
            if self.dry_run:
                print(f"[DRY RUN] Would delete {len(items)} {description} from {table_name}")
                self.actions_taken.append(f"{table_name}: Would delete {len(items)} {description}")
                return True
            
            # Delete each matching record by its partition key
            deleted_count = 0
            for item in items:
                table.delete_item(Key={pk_attr: item[pk_attr]})
                deleted_count += 1
            
            print(f"✅ Successfully deleted {deleted_count} {description} from {table_name}")
            self.actions_taken.append(f"{table_name}: Deleted {deleted_count} {description}")
            return True
            
        except ClientError as e:
            print(f"❌ ERROR: Failed to delete from {table_name}: {e}")
            return False


    # ===================================================================
    # DYNAMODB DELETION METHODS — Table-specific logic
    # ===================================================================

    def delete_access_conditions_for_relationship(self, initiator_id: str,
                                                   related_user_id: str) -> int:
        """
        Delete all AccessConditionsDB records for a single relationship.
        
        AccessConditionsDB uses a composite key:
          - PK: relationship_key  (format: "{initiator_id}#{related_user_id}")
          - SK: condition_id
        
        Each relationship in PersonaRelationshipsDB can have multiple access
        conditions (immediate, time-delayed, inactivity trigger, manual release).
        When we delete a relationship, we must cascade-delete all its conditions.
        
        This method is called from delete_persona_relationships() for each
        relationship being deleted.
        
        Args:
            initiator_id (str): The legacy maker's Cognito user ID
            related_user_id (str): The benefactor's Cognito user ID
            
        Returns:
            int: Number of access condition records deleted
        """
        table_name = self.tables['AccessConditionsDB']
        # Build the composite relationship key — same format used by the assignment functions
        relationship_key = f"{initiator_id}#{related_user_id}"
        deleted = 0
        
        try:
            table = self.dynamodb.Table(table_name)
            
            # Query all conditions for this specific relationship
            response = table.query(
                KeyConditionExpression=Key('relationship_key').eq(relationship_key)
            )
            
            items = response['Items']
            
            # Handle pagination — unlikely to have many conditions per relationship,
            # but handle it for correctness
            while 'LastEvaluatedKey' in response:
                response = table.query(
                    KeyConditionExpression=Key('relationship_key').eq(relationship_key),
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                items.extend(response['Items'])
            
            if not items:
                return 0
            
            if self.dry_run:
                print(f"      [DRY RUN] Would delete {len(items)} access conditions for {relationship_key}")
                return len(items)
            
            # Delete each condition record using the composite key
            for condition in items:
                table.delete_item(
                    Key={
                        'relationship_key': relationship_key,
                        'condition_id': condition['condition_id']
                    }
                )
                deleted += 1
                
        except ClientError as e:
            # Log warning but don't fail the whole operation — the relationship
            # itself will still be deleted even if condition cleanup fails
            print(f"   ⚠️  Warning: failed to delete AccessConditions for {relationship_key}: {e}")
        
        return deleted

    def delete_persona_relationships(self, user_id: str) -> bool:
        """
        Delete all relationship records where user is initiator or related user,
        and CASCADE DELETE all associated AccessConditionsDB records.
        
        PersonaRelationshipsDB has composite key (initiator_id, related_user_id).
        User can appear in either role, so we need to query both:
        1. As initiator (direct query on partition key)
        2. As related user (query on RelatedUserIndex GSI)
        
        For each relationship found, we also delete all access conditions from
        AccessConditionsDB that reference that relationship. This prevents orphaned
        condition records.
        
        Args:
            user_id (str): Cognito user ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        table_name = self.tables['PersonaRelationshipsDB']
        action_desc = (f"Delete all relationship records from {table_name} for user {user_id} "
                       f"(+ cascade delete AccessConditionsDB)")
        
        if not self.confirm_action(action_desc):
            return False
            
        try:
            print(f"\n🗑️  Deleting records from {table_name} (with AccessConditionsDB cascade)...")
            table = self.dynamodb.Table(table_name)
            deleted_count = 0
            conditions_deleted = 0
            
            # Query 1: Records where user is the initiator (legacy maker)
            # This is a direct query on the partition key — efficient
            response = table.query(
                KeyConditionExpression=Key('initiator_id').eq(user_id)
            )
            
            items_as_initiator = response['Items']
            
            # Handle pagination for initiator query
            while 'LastEvaluatedKey' in response:
                response = table.query(
                    KeyConditionExpression=Key('initiator_id').eq(user_id),
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                items_as_initiator.extend(response['Items'])
            
            # Query 2: Records where user is the related user (benefactor)
            # This uses the RelatedUserIndex GSI — may not exist in all environments
            try:
                response = table.query(
                    IndexName='RelatedUserIndex',  # GSI on related_user_id
                    KeyConditionExpression=Key('related_user_id').eq(user_id)
                )
                
                items_as_related = response['Items']
                
                # Handle pagination for related user query
                while 'LastEvaluatedKey' in response:
                    response = table.query(
                        IndexName='RelatedUserIndex',
                        KeyConditionExpression=Key('related_user_id').eq(user_id),
                        ExclusiveStartKey=response['LastEvaluatedKey']
                    )
                    items_as_related.extend(response['Items'])
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    print(f"   ℹ️  GSI 'RelatedUserIndex' not found, skipping related user query")
                    items_as_related = []
                else:
                    raise
            
            # Combine and deduplicate — same relationship might appear in both queries
            # if the user somehow has a self-referencing relationship (unlikely but safe)
            all_items = items_as_initiator + items_as_related
            unique_items = {f"{item['initiator_id']}#{item['related_user_id']}": item for item in all_items}
            
            if not unique_items:
                print(f"ℹ️  No relationship records found in {table_name}")
                self.actions_taken.append(f"{table_name}: No records found")
                return True
            
            if self.dry_run:
                print(f"[DRY RUN] Would delete {len(unique_items)} relationship records from {table_name}")
                # In dry run, still count how many conditions would be deleted
                for item in unique_items.values():
                    conditions_deleted += self.delete_access_conditions_for_relationship(
                        item['initiator_id'], item['related_user_id']
                    )
                self.actions_taken.append(
                    f"{table_name}: Would delete {len(unique_items)} records "
                    f"+ {conditions_deleted} AccessConditionsDB records"
                )
                return True
            
            # Delete each unique relationship and its associated access conditions
            for item in unique_items.values():
                # CASCADE: Delete access conditions FIRST, before deleting the relationship
                # This ensures we can still look up the relationship_key
                conditions_deleted += self.delete_access_conditions_for_relationship(
                    item['initiator_id'], item['related_user_id']
                )
                
                # Now delete the relationship record itself
                table.delete_item(
                    Key={
                        'initiator_id': item['initiator_id'],
                        'related_user_id': item['related_user_id']
                    }
                )
                deleted_count += 1
            
            print(f"✅ Successfully deleted {deleted_count} relationship records from {table_name}")
            if conditions_deleted > 0:
                print(f"   ↳ Also deleted {conditions_deleted} cascade records from AccessConditionsDB")
            self.actions_taken.append(
                f"{table_name}: Deleted {deleted_count} records "
                f"+ {conditions_deleted} AccessConditionsDB records"
            )
            return True
            
        except ClientError as e:
            print(f"❌ ERROR: Failed to delete from {table_name}: {e}")
            return False
    
    def delete_persona_signup_temp(self, user_id: str, email: str) -> bool:
        """
        Delete temporary signup records.
        
        PersonaSignupTempDB stores temporary data during signup process.
        The userName field might contain either the user_id or email, so try both.
        Also scans for pending invitation records where this user was invited
        as a benefactor (keyed by invite token UUID, not user_id/email).
        
        Args:
            user_id (str): Cognito user ID
            email (str): User email address
            
        Returns:
            bool: True if successful, False otherwise
        """
        table_name = self.tables['PersonaSignupTempDB']
        action_desc = f"Delete temporary signup records from {table_name}"
        
        if not self.confirm_action(action_desc):
            return False
            
        try:
            print(f"\n🗑️  Deleting records from {table_name}...")
            table = self.dynamodb.Table(table_name)
            deleted_count = 0
            
            if self.dry_run:
                print(f"[DRY RUN] Would attempt to delete records from {table_name}")
                self.actions_taken.append(f"{table_name}: Would delete records")
                return True
            
            # Attempt 1: Try to delete by user_id (userName field)
            try:
                response = table.delete_item(
                    Key={'userName': user_id},
                    ReturnValues='ALL_OLD'
                )
                if 'Attributes' in response:
                    deleted_count += 1
            except ClientError as e:
                # Ignore if item doesn't exist
                if e.response['Error']['Code'] not in ['ResourceNotFoundException', 'ConditionalCheckFailedException']:
                    raise
            
            # Attempt 2: Try to delete by email (in case it was stored as userName)
            try:
                response = table.delete_item(
                    Key={'userName': email},
                    ReturnValues='ALL_OLD'
                )
                if 'Attributes' in response:
                    deleted_count += 1
            except ClientError as e:
                # Ignore if item doesn't exist
                if e.response['Error']['Code'] not in ['ResourceNotFoundException', 'ConditionalCheckFailedException']:
                    raise
            
            # Attempt 3: Scan for pending invite records where this user was invited
            # as a benefactor. These are keyed by invite token UUID, not user_id/email,
            # so we must scan. Pattern borrowed from purge_user.py.
            try:
                scan_response = table.scan(
                    FilterExpression=Attr('benefactor_email').eq(email.lower())
                )
                for item in scan_response.get('Items', []):
                    table.delete_item(Key={'userName': item['userName']})
                    deleted_count += 1
                # Handle pagination for scan
                while 'LastEvaluatedKey' in scan_response:
                    scan_response = table.scan(
                        FilterExpression=Attr('benefactor_email').eq(email.lower()),
                        ExclusiveStartKey=scan_response['LastEvaluatedKey']
                    )
                    for item in scan_response.get('Items', []):
                        table.delete_item(Key={'userName': item['userName']})
                        deleted_count += 1
            except ClientError as e:
                # Non-critical — log and continue
                print(f"   ⚠️  Warning: scan for benefactor invites failed: {e}")
            
            if deleted_count == 0:
                print(f"ℹ️  No temporary records found in {table_name}")
                self.actions_taken.append(f"{table_name}: No records found")
            else:
                print(f"✅ Successfully deleted {deleted_count} temporary records from {table_name}")
                self.actions_taken.append(f"{table_name}: Deleted {deleted_count} records")
            
            return True
            
        except ClientError as e:
            print(f"❌ ERROR: Failed to delete from {table_name}: {e}")
            return False


    # ===================================================================
    # VERIFICATION AND SUMMARY
    # ===================================================================
    
    def verify_user_exists(self, user_id: str) -> bool:
        """
        Verify that the user still exists in Cognito after data reset.
        
        This is a safety check to ensure we didn't accidentally delete the user account.
        
        Args:
            user_id (str): Cognito user ID (Username field from Cognito)
            
        Returns:
            bool: True if user exists, False otherwise
        """
        try:
            self.cognito_client.admin_get_user(
                UserPoolId=self.user_pool_id,
                Username=user_id
            )
            return True
        except ClientError:
            return False
    
    def print_summary(self, user_id: str, email: str):
        """
        Print a summary of all actions taken during the reset process.
        
        Shows:
        - List of all operations performed
        - Verification that user account still exists
        - Next steps for testing
        
        Args:
            user_id (str): Cognito user ID
            email (str): User email address
        """
        print("\n" + "="*60)
        print("📋 DATA RESET OPERATION SUMMARY")
        print("="*60)
        
        if not self.actions_taken:
            print("❌ No actions were completed successfully")
            return
        
        print(f"✅ Successfully completed {len(self.actions_taken)} operations:")
        for i, action in enumerate(self.actions_taken, 1):
            print(f"   {i}. {action}")
        
        # Verify user account still exists - critical safety check
        print("\n" + "="*60)
        if self.verify_user_exists(user_id):
            print(f"✅ User account PRESERVED in Cognito")
            print(f"   Email: {email}")
            print(f"   User ID: {user_id}")
            print(f"   Status: Account active and ready for login")
        else:
            print(f"⚠️  WARNING: Could not verify user account in Cognito")
        
        print("\n🎯 User data reset completed successfully!")
        if not self.dry_run:
            print("⚠️  All user data has been permanently deleted.")
            print("✅ User can now log in as if it's their first time.")
        else:
            print("🔍 This was a DRY RUN - no data was actually deleted.")


    # ===================================================================
    # MAIN ORCHESTRATION
    # ===================================================================
    
    def run_reset(self, email: Optional[str] = None):
        """
        Main method to execute the complete user data reset process.
        
        This orchestrates the entire workflow:
        1. Print banner and data retention warning
        2. Get/validate user email
        3. Find user in Cognito (verify exists)
        4. Get final confirmation (type 'RESET')
        5. Delete all S3 data (4 prefixes across 2 buckets)
        6. Delete all DynamoDB data (14 tables)
        7. Print summary and verify account preserved
        
        Args:
            email (str): Optional email address (for batch mode, skips prompt)
        """
        # ---------------------------------------------------------------
        # BANNER — Tell the operator exactly what this script does
        # ---------------------------------------------------------------
        print("🔄 VIRTUAL LEGACY USER DATA RESET UTILITY 🔄")
        print("="*60)
        print("⚠️  WARNING: This will delete ALL user data but keep the account!")
        print()
        print("   S3 data to be deleted:")
        print("     - user-responses/{userId}/   (videos, thumbnails, transcripts)")
        print("     - conversations/{userId}/    (conversation audio/transcripts)")
        print("     - psych-exports/{userId}/    (psych test export files)")
        print("     - exports/{userId}/          (data export ZIPs — temp bucket)")
        print()
        print("   DynamoDB tables to be purged (14 tables):")
        print("     - userQuestionStatusDB           (answered questions)")
        print("     - userQuestionLevelProgressDB    (level progress)")
        print("     - userStatusDB                   (current level)")
        print("     - PersonaRelationshipsDB         (relationships)")
        print("     - AccessConditionsDB             (cascade from relationships)")
        print("     - PersonaSignupTempDB            (signup/invite temp data)")
        print("     - EngagementDB                   (streaks)")
        print("     - UserSubscriptionsDB            (Stripe subscription)")
        print("     - UserTestProgressDB             (in-progress psych tests)")
        print("     - UserTestResultsDB              (completed psych results)")
        print("     - DataRetentionDB                (export/deletion requests)")
        print("     - WebSocketConnectionsDB         (active connections)")
        print("     - ConversationStateDB            (in-flight conversations)")
        print("     - FeedbackReportsDB              (bug reports/feature requests)")
        print()
        print("   User will be reset to first-time login state")
        print("   ✅ Cognito account will be PRESERVED")
        print("="*60)
        
        # ---------------------------------------------------------------
        # DATA RETENTION WARNING — Important for compliance awareness
        # ---------------------------------------------------------------
        print()
        print("📋 DATA RETENTION NOTICE:")
        print("   • If this user has pending data export requests, they will be deleted.")
        print("   • If this user has a pending account deletion (grace period), it will be cleared.")
        print("   • Any exported ZIP archives in the temp bucket will be removed immediately.")
        print("   • Psychological test results will be permanently destroyed — no undo.")
        print("   • Stripe subscription record will be deleted (does NOT cancel Stripe itself).")
        print("   • This utility is intended for TEST ACCOUNTS ONLY.")
        print()
        
        # ---------------------------------------------------------------
        # Step 1: Get user email (interactive or from parameter)
        # ---------------------------------------------------------------
        if not email:
            email = self.get_user_email()
        else:
            print(f"\n📧 Using provided email: {email}")
        
        # ---------------------------------------------------------------
        # Step 2: Find user in Cognito — verify they exist before deleting anything
        # ---------------------------------------------------------------
        user_data = self.find_cognito_user(email)
        if not user_data:
            print(f"\n❌ Cannot proceed: User '{email}' not found in system")
            return
        
        user_id = user_data['Username']  # Cognito sub (UUID)
        
        print(f"\n📊 USER FOUND:")
        print(f"   Email: {email}")
        print(f"   User ID: {user_id}")
        print(f"   Status: {user_data.get('UserStatus', 'Unknown')}")
        
        # ---------------------------------------------------------------
        # Step 3: Final confirmation before starting destructive operations
        # After this, self.confirmed = True and no more prompts will appear
        # ---------------------------------------------------------------
        if not self.dry_run:
            final_confirm = input(f"\n🚨 FINAL CONFIRMATION: Reset ALL data for user '{email}'? (type 'RESET' to confirm): ")
            if final_confirm != 'RESET':
                print("❌ Operation cancelled. User did not type 'RESET'")
                return
            # User confirmed - set flag to skip individual operation confirmations
            self.confirmed = True
        
        print(f"\n🚀 Starting data reset process for user '{email}'...")
        
        # ===============================================================
        # Step 4: Delete S3 files
        # 3 prefixes in the main virtual-legacy bucket + 1 in exports temp bucket
        # ===============================================================
        print("\n" + "="*60)
        print("[S3 OPERATIONS — virtual-legacy bucket]")
        print("="*60)
        
        # S3 prefix 1: user-responses — video recordings, thumbnails, transcripts
        self.delete_s3_files(user_id, f"user-responses/{user_id}/", "user-responses")
        
        # S3 prefix 2: conversations — conversation audio and transcripts
        self.delete_s3_files(user_id, f"conversations/{user_id}/", "conversations")
        
        # S3 prefix 3: psych-exports — psychological test export files (PDF/CSV)
        # Added 2026-04-26: psych testing framework stores exports at psych-exports/{userId}/
        self.delete_s3_files(user_id, f"psych-exports/{user_id}/", "psych-exports")
        
        print("\n" + "="*60)
        print(f"[S3 OPERATIONS — {self.exports_temp_bucket} bucket]")
        print("="*60)
        
        # S3 prefix 4: exports — data export ZIP archives (GDPR/content packages)
        # Added 2026-04-26: data retention system stores exports at exports/{userId}/
        # This bucket has a 7-day lifecycle rule, but we clean up immediately
        # so the test account reset is thorough.
        self.delete_s3_files(
            user_id,
            f"exports/{user_id}/",
            "data-exports (temp bucket)",
            bucket=self.exports_temp_bucket
        )
        
        # ===============================================================
        # Step 5: Delete DynamoDB records from all 14 tables
        # ===============================================================
        print("\n" + "="*60)
        print("[DYNAMODB OPERATIONS — Core question/progress tables]")
        print("="*60)
        
        # Table 1: userQuestionStatusDB — answered questions
        # Composite key: userId (PK) + questionId (SK)
        self.delete_dynamodb_table_by_partition_key(
            self.tables['userQuestionStatusDB'], 
            'userId', 
            user_id, 
            'questionId'
        )
        
        # Table 2: userQuestionLevelProgressDB — level progress per question type
        # Composite key: userId (PK) + questionType (SK)
        self.delete_dynamodb_table_by_partition_key(
            self.tables['userQuestionLevelProgressDB'], 
            'userId', 
            user_id, 
            'questionType'
        )
        
        # Table 3: userStatusDB — current global level
        # Simple key: userId (PK)
        self.delete_dynamodb_single_item(
            self.tables['userStatusDB'], 
            {'userId': user_id}
        )
        
        print("\n" + "="*60)
        print("[DYNAMODB OPERATIONS — Relationships + Access Conditions]")
        print("="*60)
        
        # Table 4 + 5: PersonaRelationshipsDB + AccessConditionsDB (cascade)
        # PersonaRelationshipsDB: Composite key: initiator_id (PK) + related_user_id (SK)
        # AccessConditionsDB: Composite key: relationship_key (PK) + condition_id (SK)
        # The delete_persona_relationships method handles both tables — it deletes
        # all relationships where the user is initiator OR related user, and for each
        # relationship it cascade-deletes all access conditions from AccessConditionsDB.
        self.delete_persona_relationships(user_id)
        
        print("\n" + "="*60)
        print("[DYNAMODB OPERATIONS — Signup, Engagement, Subscription]")
        print("="*60)
        
        # Table 6: PersonaSignupTempDB — temporary signup / invitation data
        # Simple key: userName (PK) — may contain userId, email, or invite token
        self.delete_persona_signup_temp(user_id, email)
        
        # Table 7: EngagementDB — streak and engagement tracking
        # Simple key: userId (PK)
        self.delete_dynamodb_single_item(
            self.tables['EngagementDB'], 
            {'userId': user_id}
        )
        
        # Table 8: UserSubscriptionsDB — Stripe subscription and billing tier
        # Simple key: userId (PK)
        # NOTE: This deletes the DynamoDB record only. It does NOT cancel the
        # Stripe subscription itself. For test accounts this is fine — the Stripe
        # test mode subscription will remain in Stripe's dashboard but the app
        # will treat the user as free tier on next login.
        # Added 2026-04-26: Stripe billing system was added ~Mar 2026
        self.delete_dynamodb_single_item(
            self.tables['UserSubscriptionsDB'],
            {'userId': user_id}
        )
        
        print("\n" + "="*60)
        print("[DYNAMODB OPERATIONS — Psychological Testing]")
        print("="*60)
        
        # Table 9: UserTestProgressDB — in-progress psych test responses
        # Composite key: userId (PK) + testId (SK)
        # Has TTL (expiresAt) so records auto-expire, but we delete explicitly
        # for a clean reset.
        # Added 2026-04-26: psych testing framework was added ~Mar 2026
        self.delete_dynamodb_table_by_partition_key(
            self.tables['UserTestProgressDB'],
            'userId',
            user_id,
            'testId'
        )
        
        # Table 10: UserTestResultsDB — completed psych test results and scores
        # Composite key: userId (PK) + testIdVersionTimestamp (SK)
        # These are the user's actual psychological assessment results — permanently
        # destroyed by this operation. No undo.
        # Added 2026-04-26: psych testing framework was added ~Mar 2026
        self.delete_dynamodb_table_by_partition_key(
            self.tables['UserTestResultsDB'],
            'userId',
            user_id,
            'testIdVersionTimestamp'
        )
        
        print("\n" + "="*60)
        print("[DYNAMODB OPERATIONS — Data Retention / Exports]")
        print("="*60)
        
        # Table 11: DataRetentionDB — export requests, deletion requests, dormancy tracking
        # Composite key: userId (PK) + recordType (SK)
        # Unlike the production account deletion Lambda (which preserves the
        # deletion_request record), we delete ALL records here because this is
        # a test account reset — we want a completely clean slate.
        # Added 2026-04-26: data retention lifecycle was added ~Mar 2026
        self.delete_dynamodb_table_by_partition_key(
            self.tables['DataRetentionDB'],
            'userId',
            user_id,
            'recordType'
        )
        
        print("\n" + "="*60)
        print("[DYNAMODB OPERATIONS — Transient / Connection tables]")
        print("="*60)
        
        # Table 12: WebSocketConnectionsDB — active WebSocket connections
        # Simple key: connectionId (PK), but userId is stored as an attribute.
        # Must scan the table to find connections for this user.
        # These records have TTL and auto-expire, but we clean up explicitly.
        self.delete_dynamodb_by_scan(
            self.tables['WebSocketConnectionsDB'],
            'userId',
            user_id,
            'connectionId',
            'WebSocket connections'
        )
        
        # Table 13: ConversationStateDB — in-flight conversation state
        # Simple key: connectionId (PK), but userId is stored as an attribute.
        # Must scan the table to find conversation states for this user.
        # These records have TTL and auto-expire, but we clean up explicitly.
        # Added 2026-04-26: this table existed but was not in the original utility
        self.delete_dynamodb_by_scan(
            self.tables['ConversationStateDB'],
            'userId',
            user_id,
            'connectionId',
            'conversation states'
        )
        
        print("\n" + "="*60)
        print("[DYNAMODB OPERATIONS — Feedback]")
        print("="*60)
        
        # Table 14: FeedbackReportsDB — user-submitted bug reports and feature requests
        # Simple key: reportId (PK), but userId is stored as an attribute.
        # Must scan the table to find reports submitted by this user.
        # Added 2026-04-26: feedback system was added ~Apr 2026
        self.delete_dynamodb_by_scan(
            self.tables['FeedbackReportsDB'],
            'userId',
            user_id,
            'reportId',
            'feedback reports'
        )
        
        # ===============================================================
        # Step 6: Print summary and verify account preserved
        # ===============================================================
        self.print_summary(user_id, email)
        
        # Overall success message
        if not self.dry_run:
            print(f"\n🎉 DATA RESET COMPLETED SUCCESSFULLY for user '{email}'")
            print("   User account is preserved and ready for testing!")
        else:
            print(f"\n🔍 DRY RUN COMPLETED for user '{email}'")
            print("   Run without --dry-run flag to actually delete data")



def main():
    """
    Main entry point for the user data reset utility.
    
    Parses command line arguments and runs the reset process.
    Supports:
    - Interactive mode (no args)
    - Dry run mode (--dry-run)
    - Batch mode (--email)
    - Combined (--email --dry-run)
    """
    parser = argparse.ArgumentParser(
        description='Reset Virtual Legacy user data while preserving the account',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode with confirmation prompts
  python purgeUserProgressAndDataButKeepUser.py
  
  # Dry run to see what would be deleted
  python purgeUserProgressAndDataButKeepUser.py --dry-run
  
  # Batch mode with email provided
  python purgeUserProgressAndDataButKeepUser.py --email user@example.com
  
  # Dry run with specific email
  python purgeUserProgressAndDataButKeepUser.py --email user@example.com --dry-run
        """
    )
    
    parser.add_argument(
        '--email',
        type=str,
        help='Email address of the user to reset (skips interactive prompt)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deleted without actually deleting'
    )
    
    args = parser.parse_args()
    
    try:
        reset_utility = VirtualLegacyUserDataReset(dry_run=args.dry_run)
        reset_utility.run_reset(email=args.email)
    except KeyboardInterrupt:
        print("\n\n❌ Operation cancelled by user (Ctrl+C)")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
