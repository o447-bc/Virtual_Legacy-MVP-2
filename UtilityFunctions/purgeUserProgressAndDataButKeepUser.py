#!/usr/bin/env python3
"""
Virtual Legacy User Data Reset Utility

This utility safely deletes all user data from the Virtual Legacy system while
preserving the Cognito user account. This allows testing first-time login scenarios.

Data Deleted:
- S3 video response files (user-responses/)
- S3 conversation files (conversations/)
- DynamoDB records across all user data tables

Data Preserved:
- Cognito User Pool account (email, password, authentication)

CAUTION: This script permanently deletes user data. Use for testing only.

Author: Kiro AI Assistant
Date: 2026-02-21
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
    - Deletes all S3 files (videos, audio, transcripts)
    - Deletes all DynamoDB records (progress, status, relationships)
    - Preserves Cognito user account
    - Supports dry-run mode for safe testing
    - Single confirmation for all operations (no per-step prompts)
    """
    
    def __init__(self, dry_run: bool = False):
        """
        Initialize AWS clients and configuration.
        
        Sets up connections to Cognito, S3, and DynamoDB services.
        Configures table names and bucket information.
        
        Args:
            dry_run (bool): If True, show what would be deleted without actually deleting
        """
        try:
            # AWS service clients - all in us-east-1 region
            self.cognito_client = boto3.client('cognito-idp', region_name='us-east-1')
            self.s3_client = boto3.client('s3', region_name='us-east-1')
            self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
            
            # Configuration from SAM template
            self.user_pool_id = 'us-east-1_KsG65yYlo'  # Virtual Legacy Cognito User Pool
            self.s3_bucket = 'virtual-legacy'  # Main S3 bucket for all user data
            
            # DynamoDB table names - all tables that contain user-specific data
            self.tables = {
                'userQuestionStatusDB': 'userQuestionStatusDB',  # Answered questions tracking
                'userQuestionLevelProgressDB': 'userQuestionLevelProgressDB',  # Level progress per question type
                'userStatusDB': 'userStatusDB',  # Current global level
                'PersonaRelationshipsDB': 'PersonaRelationshipsDB',  # User relationships
                'PersonaSignupTempDB': 'PersonaSignupTempDB',  # Temporary signup data
                'EngagementDB': 'EngagementDB',  # Streak and engagement tracking
                'WebSocketConnectionsDB': 'WebSocketConnectionsDB'  # Active WebSocket connections
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
    
    def delete_s3_files(self, user_id: str, prefix: str, description: str) -> bool:
        """
        Delete all S3 files for the specified prefix.
        
        Uses pagination to handle large numbers of files.
        Deletes in batches of 1000 (S3 API limit).
        
        Args:
            user_id (str): Cognito user ID (used in confirmation message)
            prefix (str): S3 prefix to delete (e.g., "user-responses/{userId}/")
            description (str): Human-readable description for logging (e.g., "user-responses")
            
        Returns:
            bool: True if successful, False otherwise
        """
        action_desc = f"Delete all S3 files from {prefix}"
        if not self.confirm_action(action_desc):
            return False
            
        try:
            print(f"\n🗑️  Deleting S3 files from {prefix}...")
            
            # List objects with prefix (with pagination support for large datasets)
            paginator = self.s3_client.get_paginator('list_objects_v2')
            
            all_objects = []
            for page in paginator.paginate(Bucket=self.s3_bucket, Prefix=prefix):
                if 'Contents' in page:
                    all_objects.extend(page['Contents'])
            
            if not all_objects:
                print(f"ℹ️  No S3 files found at {prefix}")
                self.actions_taken.append(f"S3 {description}: No files found")
                return True
            
            if self.dry_run:
                print(f"[DRY RUN] Would delete {len(all_objects)} files from {prefix}")
                self.actions_taken.append(f"S3 {description}: Would delete {len(all_objects)} files")
                return True
            
            # Delete objects in batches (S3 delete_objects supports max 1000 objects per call)
            total_deleted = 0
            batch_size = 1000
            
            for i in range(0, len(all_objects), batch_size):
                batch = all_objects[i:i + batch_size]
                objects_to_delete = [{'Key': obj['Key']} for obj in batch]
                
                delete_response = self.s3_client.delete_objects(
                    Bucket=self.s3_bucket,
                    Delete={'Objects': objects_to_delete}
                )
                
                batch_deleted = len(delete_response.get('Deleted', []))
                total_deleted += batch_deleted
                print(f"   Deleted batch: {batch_deleted} files")
            
            print(f"✅ Successfully deleted {total_deleted} S3 files total")
            self.actions_taken.append(f"S3 {description}: Deleted {total_deleted} files")
            
            return True
            
        except ClientError as e:
            print(f"❌ ERROR: Failed to delete S3 files from {prefix}: {
    
    def delete_dynamodb_table_by_partition_key(self, table_name: str, key_name: str, 
                                                key_value: str, sort_key_name: Optional[str] = None) -> bool:
        """
        Delete all records from a DynamoDB table by partition key.
        
        Queries the table for all records matching the partition key,
        then deletes each record individually. Handles pagination for large datasets.
        
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
        
        Used for tables where user has only one record (e.g., userStatusDB, EngagementDB).
        
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

    def delete_persona_relationships(self, user_id: str) -> bool:
        """
        Delete all relationship records where user is initiator or related user.
        
        PersonaRelationshipsDB has composite key (initiator_id, related_user_id).
        User can appear in either role, so we need to query both:
        1. As initiator (direct query on partition key)
        2. As related user (query on GSI if available)
        
        Args:
            user_id (str): Cognito user ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        table_name = self.tables['PersonaRelationshipsDB']
        action_desc = f"Delete all relationship records from {table_name} for user {user_id}"
        
        if not self.confirm_action(action_desc):
            return False
            
        try:
            print(f"\n🗑️  Deleting records from {table_name}...")
            table = self.dynamodb.Table(table_name)
            deleted_count = 0
            
            # Query 1: Delete records where user is the initiator
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
            
            # Query 2: Delete records where user is the related user (using GSI)
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
            
            # Combine and deduplicate - same relationship might appear in both queries
            all_items = items_as_initiator + items_as_related
            unique_items = {f"{item['initiator_id']}#{item['related_user_id']}": item for item in all_items}
            
            if not unique_items:
                print(f"ℹ️  No relationship records found in {table_name}")
                self.actions_taken.append(f"{table_name}: No records found")
                return True
            
            if self.dry_run:
                print(f"[DRY RUN] Would delete {len(unique_items)} relationship records from {table_name}")
                self.actions_taken.append(f"{table_name}: Would delete {len(unique_items)} records")
                return True
            
            # Delete each unique relationship using composite key
            for item in unique_items.values():
                table.delete_item(
                    Key={
                        'initiator_id': item['initiator_id'],
                        'related_user_id': item['related_user_id']
                    }
                )
                deleted_count += 1
            
            print(f"✅ Successfully deleted {deleted_count} relationship records from {table_name}")
            self.actions_taken.append(f"{table_name}: Deleted {deleted_count} records")
            return True
            
        except ClientError as e:
            print(f"❌ ERROR: Failed to delete from {table_name}: {e}")
            return False
    
    def delete_persona_signup_temp(self, user_id: str, email: str) -> bool:
        """
        Delete temporary signup records.
        
        PersonaSignupTempDB stores temporary data during signup process.
        The userName field might contain either the user_id or email, so try both.
        
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
            
            # Try to delete by user_id (userName field)
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
            
            # Try to delete by email (in case it was stored as userName)
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
    
    def delete_websocket_connections(self, user_id: str) -> bool:
        """
        Delete WebSocket connection records for the user.
        
        WebSocketConnectionsDB uses connectionId as partition key, but stores userId as attribute.
        Must scan the table to find all connections for this user.
        
        Args:
            user_id (str): Cognito user ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        table_name = self.tables['WebSocketConnectionsDB']
        action_desc = f"Delete WebSocket connections from {table_name} for user {user_id}"
        
        if not self.confirm_action(action_desc):
            return False
            
        try:
            print(f"\n🗑️  Deleting records from {table_name}...")
            table = self.dynamodb.Table(table_name)
            
            # Scan table for userId attribute (can't query because userId is not the key)
            response = table.scan(
                FilterExpression=Attr('userId').eq(user_id)
            )
            
            items = response['Items']
            
            # Handle pagination for scan
            while 'LastEvaluatedKey' in response:
                response = table.scan(
                    FilterExpression=Attr('userId').eq(user_id),
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                items.extend(response['Items'])
            
            if not items:
                print(f"ℹ️  No WebSocket connections found in {table_name}")
                self.actions_taken.append(f"{table_name}: No connections found")
                return True
            
            if self.dry_run:
                print(f"[DRY RUN] Would delete {len(items)} WebSocket connections from {table_name}")
                self.actions_taken.append(f"{table_name}: Would delete {len(items)} connections")
                return True
            
            # Delete each connection by connectionId
            deleted_count = 0
            for item in items:
                table.delete_item(Key={'connectionId': item['connectionId']})
                deleted_count += 1
            
            print(f"✅ Successfully deleted {deleted_count} WebSocket connections from {table_name}")
            self.actions_taken.append(f"{table_name}: Deleted {deleted_count} connections")
            return True
            
        except ClientError as e:
            print(f"❌ ERROR: Failed to delete from {table_name}: {e}")
            return False
    
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
    
    def run_reset(self, email: Optional[str] = None):
        """
        Main method to execute the complete user data reset process.
        
        This orchestrates the entire workflow:
        1. Get/validate user email
        2. Find user in Cognito (verify exists)
        3. Get final confirmation (type 'RESET')
        4. Delete all S3 data (videos, conversations)
        5. Delete all DynamoDB data (7 tables)
        6. Print summary and verify account preserved
        
        Args:
            email (str): Optional email address (for batch mode, skips prompt)
        """
        print("🔄 VIRTUAL LEGACY USER DATA RESET UTILITY 🔄")
        print("="*60)
        print("⚠️  WARNING: This will delete ALL user data but keep the account!")
        print("   - All S3 video responses and conversations")
        print("   - All DynamoDB progress and status records")
        print("   - User will be reset to first-time login state")
        print("   ✅ Cognito account will be PRESERVED")
        print("="*60)
        
        # Step 1: Get user email (interactive or from parameter)
        if not email:
            email = self.get_user_email()
        else:
            print(f"\n📧 Using provided email: {email}")
        
        # Step 2: Find user in Cognito - verify they exist before deleting anything
        user_data = self.find_cognito_user(email)
        if not user_data:
            print(f"\n❌ Cannot proceed: User '{email}' not found in system")
            return
        
        user_id = user_data['Username']  # Cognito sub (UUID)
        
        print(f"\n📊 USER FOUND:")
        print(f"   Email: {email}")
        print(f"   User ID: {user_id}")
        print(f"   Status: {user_data.get('UserStatus', 'Unknown')}")
        
        # Step 3: Final confirmation before starting destructive operations
        # After this, self.confirmed = True and no more prompts will appear
        if not self.dry_run:
            final_confirm = input(f"\n🚨 FINAL CONFIRMATION: Reset ALL data for user '{email}'? (type 'RESET' to confirm): ")
            if final_confirm != 'RESET':
                print("❌ Operation cancelled. User did not type 'RESET'")
                return
            # User confirmed - set flag to skip individual operation confirmations
            self.confirmed = True
        
        print(f"\n🚀 Starting data reset process for user '{email}'...")
        
        # Step 4: Delete S3 files
        # Two prefixes: user-responses (videos) and conversations (audio/transcripts)
        print("\n" + "="*60)
        print("[S3 OPERATIONS]")
        print("="*60)
        
        self.delete_s3_files(user_id, f"user-responses/{user_id}/", "user-responses")
        self.delete_s3_files(user_id, f"conversations/{user_id}/", "conversations")
        
        # Step 5: Delete DynamoDB records from all 7 tables
        print("\n" + "="*60)
        print("[DYNAMODB OPERATIONS]")
        print("="*60)
        
        # Table 1: userQuestionStatusDB - answered questions (userId + questionId)
        self.delete_dynamodb_table_by_partition_key(
            self.tables['userQuestionStatusDB'], 
            'userId', 
            user_id, 
            'questionId'  # Composite key
        )
        
        # Table 2: userQuestionLevelProgressDB - level progress (userId + questionType)
        self.delete_dynamodb_table_by_partition_key(
            self.tables['userQuestionLevelProgressDB'], 
            'userId', 
            user_id, 
            'questionType'  # Composite key
        )
        
        # Table 3: userStatusDB - current level (userId only)
        self.delete_dynamodb_single_item(
            self.tables['userStatusDB'], 
            {'userId': user_id}
        )
        
        # Table 4: PersonaRelationshipsDB - relationships (special handling for both roles)
        self.delete_persona_relationships(user_id)
        
        # Table 5: PersonaSignupTempDB - temporary signup data (try both userId and email)
        self.delete_persona_signup_temp(user_id, email)
        
        # Table 6: EngagementDB - streak data (userId only)
        self.delete_dynamodb_single_item(
            self.tables['EngagementDB'], 
            {'userId': user_id}
        )
        
        # Table 7: WebSocketConnectionsDB - active connections (scan by userId attribute)
        self.delete_websocket_connections(user_id)
        
        # Step 6: Print summary and verify account preserved
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
