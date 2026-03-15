#!/usr/bin/env python3
"""
Virtual Legacy User Purge Utility

This utility safely deletes all user data from the Virtual Legacy system including:
- Cognito User Pool account
- S3 video response files
- DynamoDB records across multiple tables

DANGER: This script permanently deletes user data. Use with extreme caution.

Author: Amazon Q Developer
Date: 2025-01-07
"""

import boto3
import json
import sys
from typing import Optional, List, Dict, Any
from botocore.exceptions import ClientError, NoCredentialsError
from boto3.dynamodb.conditions import Key


class VirtualLegacyUserPurge:
    """
    Comprehensive user data purge utility for Virtual Legacy system.
    
    This class handles the complete removal of user data across all AWS services
    used by the Virtual Legacy application, including Cognito, S3, and DynamoDB.
    """
    
    def __init__(self):
        """Initialize AWS clients and configuration."""
        try:
            # AWS service clients
            self.cognito_client = boto3.client('cognito-idp', region_name='us-east-1')
            self.s3_client = boto3.client('s3', region_name='us-east-1')
            self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
            
            # Configuration from SAM template
            self.user_pool_id = 'us-east-1_KsG65yYlo'
            self.s3_bucket = 'virtual-legacy'
            
            # DynamoDB table names
            self.tables = {
                'userQuestionStatusDB': 'userQuestionStatusDB',
                'PersonaRelationshipsDB': 'PersonaRelationshipsDB', 
                'AccessConditionsDB': 'AccessConditionsDB',
                'PersonaSignupTempDB': 'PersonaSignupTempDB',
                'userStatusDB': 'userStatusDB'
            }
            
            # Summary of actions taken
            self.actions_taken = []
            
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
        
        Returns:
            str: Validated email address in lowercase
        """
        while True:
            email = input("\n📧 Enter the email address of the user to purge: ").strip()
            
            if not email:
                print("❌ Email address cannot be empty. Please try again.")
                continue
                
            # Basic email validation
            if '@' not in email or '.' not in email.split('@')[1]:
                print("❌ Invalid email format. Please enter a valid email address.")
                continue
                
            # Convert to lowercase for consistency
            email = email.lower()
            
            # Confirm email address
            confirm = input(f"\n⚠️  CONFIRM: You want to purge user '{email}'? (yes/no): ").strip().lower()
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
        
        Args:
            email (str): Email address to search for
            
        Returns:
            Optional[Dict]: User data if found, None otherwise
        """
        try:
            print(f"\n🔍 Searching for user '{email}' in Cognito User Pool...")
            
            # List all users and find by email
            paginator = self.cognito_client.get_paginator('list_users')
            
            for page in paginator.paginate(UserPoolId=self.user_pool_id):
                for user in page['Users']:
                    # Check email attribute
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
        
        Args:
            action_description (str): Description of the action to be performed
            
        Returns:
            bool: True if user confirms, False otherwise
        """
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
    
    def delete_s3_files(self, user_id: str) -> bool:
        """
        Delete all S3 files for the specified user.
        
        Args:
            user_id (str): Cognito user ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print(f"\n🗑️  Deleting S3 files for user {user_id}...")
            
            # List objects with user ID prefix (with pagination support)
            prefix = f"user-responses/{user_id}/"
            paginator = self.s3_client.get_paginator('list_objects_v2')
            
            all_objects = []
            for page in paginator.paginate(Bucket=self.s3_bucket, Prefix=prefix):
                if 'Contents' in page:
                    all_objects.extend(page['Contents'])
            
            if not all_objects:
                print(f"ℹ️  No S3 files found for user {user_id}")
                self.actions_taken.append(f"S3: No files found for user {user_id}")
                return True
            
            # Delete objects in batches (S3 delete_objects supports max 1000 objects)
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
            self.actions_taken.append(f"S3: Deleted {total_deleted} files for user {user_id}")
            
            return True
            
        except ClientError as e:
            print(f"❌ ERROR: Failed to delete S3 files: {e}")
            return False
    
    def delete_dynamodb_records(self, user_id: str, email: str) -> bool:
        """
        Delete all DynamoDB records for the specified user across all tables.
        
        Args:
            user_id (str): Cognito user ID
            email (str): User email address
            
        Returns:
            bool: True if successful, False otherwise
        """
        success = True
        
        # Delete from userQuestionStatusDB
        success &= self._delete_user_question_status(user_id)
        
        # Delete from PersonaRelationshipsDB (as both initiator and related user)
        success &= self._delete_persona_relationships(user_id)
        
        # Delete from PersonaSignupTempDB
        success &= self._delete_persona_signup_temp(user_id, email)
        
        # Delete from userStatusDB
        success &= self._delete_user_status(user_id)
        
        return success
    
    def _delete_user_question_status(self, user_id: str) -> bool:
        """Delete records from userQuestionStatusDB table."""
        table_name = self.tables['userQuestionStatusDB']
        try:
            print(f"\n🗑️  Deleting records from {table_name}...")
            table = self.dynamodb.Table(table_name)
            
            # Query all records for this user
            response = table.query(
                KeyConditionExpression=Key('userId').eq(user_id)
            )
            
            items = response['Items']
            if not items:
                print(f"ℹ️  No records found in {table_name} for user {user_id}")
                self.actions_taken.append(f"{table_name}: No records found for user {user_id}")
                return True
            
            # Delete each record
            deleted_count = 0
            for item in items:
                table.delete_item(
                    Key={
                        'userId': item['userId'],
                        'questionId': item['questionId']
                    }
                )
                deleted_count += 1
            
            print(f"✅ Successfully deleted {deleted_count} records from {table_name}")
            self.actions_taken.append(f"{table_name}: Deleted {deleted_count} records for user {user_id}")
            return True
            
        except ClientError as e:
            print(f"❌ ERROR: Failed to delete from {table_name}: {e}")
            return False
    
    def _delete_access_conditions_for_relationship(self, initiator_id: str, related_user_id: str) -> int:
        """Delete all AccessConditionsDB records for a given relationship. Returns count deleted."""
        conditions_table = self.dynamodb.Table(self.tables['AccessConditionsDB'])
        relationship_key = f"{initiator_id}#{related_user_id}"
        deleted = 0
        try:
            response = conditions_table.query(
                KeyConditionExpression=Key('relationship_key').eq(relationship_key)
            )
            for condition in response['Items']:
                conditions_table.delete_item(
                    Key={
                        'relationship_key': relationship_key,
                        'condition_id': condition['condition_id']
                    }
                )
                deleted += 1
        except ClientError as e:
            print(f"   ⚠️  Warning: failed to delete AccessConditions for {relationship_key}: {e}")
        return deleted

    def _delete_persona_relationships(self, user_id: str) -> bool:
        """Delete records from PersonaRelationshipsDB table and cascade to AccessConditionsDB."""
        table_name = self.tables['PersonaRelationshipsDB']
        try:
            print(f"\n🗑️  Deleting records from {table_name}...")
            table = self.dynamodb.Table(table_name)
            deleted_count = 0
            conditions_deleted = 0

            # Collect all relationships to delete (as initiator and as related user)
            relationships = []

            response = table.query(
                KeyConditionExpression=Key('initiator_id').eq(user_id)
            )
            relationships.extend(response['Items'])

            response = table.query(
                IndexName='RelatedUserIndex',
                KeyConditionExpression=Key('related_user_id').eq(user_id)
            )
            relationships.extend(response['Items'])

            for item in relationships:
                # Cascade delete AccessConditionsDB records first
                conditions_deleted += self._delete_access_conditions_for_relationship(
                    item['initiator_id'], item['related_user_id']
                )
                table.delete_item(
                    Key={
                        'initiator_id': item['initiator_id'],
                        'related_user_id': item['related_user_id']
                    }
                )
                deleted_count += 1

            if deleted_count == 0:
                print(f"ℹ️  No relationship records found in {table_name} for user {user_id}")
                self.actions_taken.append(f"{table_name}: No records found for user {user_id}")
            else:
                print(f"✅ Successfully deleted {deleted_count} relationship records from {table_name} "
                      f"and {conditions_deleted} access condition records from AccessConditionsDB")
                self.actions_taken.append(
                    f"{table_name}: Deleted {deleted_count} records + "
                    f"{conditions_deleted} AccessConditionsDB records for user {user_id}"
                )

            return True

        except ClientError as e:
            print(f"❌ ERROR: Failed to delete from {table_name}: {e}")
            return False
    
    def _delete_persona_signup_temp(self, user_id: str, email: str) -> bool:
        """Delete records from PersonaSignupTempDB table, including pending invites by benefactor_email."""
        table_name = self.tables['PersonaSignupTempDB']
        try:
            print(f"\n🗑️  Deleting records from {table_name}...")
            table = self.dynamodb.Table(table_name)
            deleted_count = 0

            # Try to delete by user_id (userName field)
            try:
                response = table.delete_item(Key={'userName': user_id}, ReturnValues='ALL_OLD')
                if 'Attributes' in response:
                    deleted_count += 1
            except ClientError as e:
                if e.response['Error']['Code'] not in ['ResourceNotFoundException', 'ConditionalCheckFailedException']:
                    raise

            # Try to delete by email (in case it was stored as userName)
            try:
                response = table.delete_item(Key={'userName': email}, ReturnValues='ALL_OLD')
                if 'Attributes' in response:
                    deleted_count += 1
            except ClientError as e:
                if e.response['Error']['Code'] not in ['ResourceNotFoundException', 'ConditionalCheckFailedException']:
                    raise

            # Scan for pending invite records where this user was invited as a benefactor
            # (these are keyed by invite token UUID, not user_id/email)
            from boto3.dynamodb.conditions import Attr
            scan_response = table.scan(
                FilterExpression=Attr('benefactor_email').eq(email.lower())
            )
            for item in scan_response.get('Items', []):
                table.delete_item(Key={'userName': item['userName']})
                deleted_count += 1

            if deleted_count == 0:
                print(f"ℹ️  No temporary records found in {table_name} for user {user_id}")
                self.actions_taken.append(f"{table_name}: No records found for user {user_id}")
            else:
                print(f"✅ Successfully deleted {deleted_count} temporary records from {table_name}")
                self.actions_taken.append(f"{table_name}: Deleted {deleted_count} records for user {user_id}")

            return True

        except ClientError as e:
            print(f"❌ ERROR: Failed to delete from {table_name}: {e}")
            return False
    
    def _delete_user_status(self, user_id: str) -> bool:
        """Delete records from userStatusDB table."""
        table_name = self.tables['userStatusDB']
        try:
            print(f"\n🗑️  Deleting record from {table_name}...")
            table = self.dynamodb.Table(table_name)
            
            response = table.delete_item(
                Key={'userId': user_id},
                ReturnValues='ALL_OLD'
            )
            
            if 'Attributes' in response:
                print(f"✅ Successfully deleted user status record from {table_name}")
                self.actions_taken.append(f"{table_name}: Deleted record for user {user_id}")
            else:
                print(f"ℹ️  No record found in {table_name} for user {user_id}")
                self.actions_taken.append(f"{table_name}: No record found for user {user_id}")
            
            return True
            
        except ClientError as e:
            print(f"❌ ERROR: Failed to delete from {table_name}: {e}")
            return False
    
    def delete_cognito_user(self, username: str) -> bool:
        """
        Delete user from Cognito User Pool.
        
        Args:
            username (str): Cognito username
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print(f"\n🗑️  Deleting user '{username}' from Cognito...")
            
            self.cognito_client.admin_delete_user(
                UserPoolId=self.user_pool_id,
                Username=username
            )
            
            print(f"✅ Successfully deleted user '{username}' from Cognito")
            self.actions_taken.append(f"Cognito: Deleted user {username}")
            return True
            
        except ClientError as e:
            print(f"❌ ERROR: Failed to delete Cognito user: {e}")
            return False
    
    def print_summary(self):
        """Print a summary of all actions taken during the purge process."""
        print("\n" + "="*60)
        print("📋 PURGE OPERATION SUMMARY")
        print("="*60)
        
        if not self.actions_taken:
            print("❌ No actions were completed successfully")
            return
        
        print(f"✅ Successfully completed {len(self.actions_taken)} actions:")
        for i, action in enumerate(self.actions_taken, 1):
            print(f"   {i}. {action}")
        
        print("\n🎯 User data purge completed successfully!")
        print("⚠️  All data for this user has been permanently deleted.")
    
    def run_purge(self):
        """
        Main method to execute the complete user purge process.
        
        This method orchestrates the entire purge workflow:
        1. Get user email
        2. Find user in Cognito
        3. Delete S3 files
        4. Delete DynamoDB records
        5. Delete Cognito user
        6. Print summary
        """
        print("🚨 VIRTUAL LEGACY USER PURGE UTILITY 🚨")
        print("="*50)
        print("⚠️  WARNING: This will permanently delete ALL user data!")
        print("   - Cognito user account")
        print("   - All S3 video response files")
        print("   - All DynamoDB records across multiple tables")
        print("="*50)
        
        # Step 1: Get user email
        email = self.get_user_email()
        
        # Step 2: Find user in Cognito
        user_data = self.find_cognito_user(email)
        if not user_data:
            print(f"\n❌ Cannot proceed: User '{email}' not found in system")
            return
        
        user_id = user_data['Username']
        
        print(f"\n📊 USER FOUND:")
        print(f"   Email: {email}")
        print(f"   User ID: {user_id}")
        print(f"   Status: {user_data.get('UserStatus', 'Unknown')}")
        
        # Final confirmation before starting destructive operations
        final_confirm = input(f"\n🚨 FINAL CONFIRMATION: Delete ALL data for user '{email}'? (type 'DELETE' to confirm): ")
        if final_confirm != 'DELETE':
            print("❌ Operation cancelled. User typed something other than 'DELETE'")
            return
        
        print(f"\n🚀 Starting purge process for user '{email}'...")
        
        # Step 3: Delete S3 files
        s3_success = self.delete_s3_files(user_id)
        
        # Step 4: Delete DynamoDB records
        db_success = self.delete_dynamodb_records(user_id, email)
        
        # Step 5: Delete Cognito user
        cognito_success = self.delete_cognito_user(user_id)
        
        # Step 6: Print summary
        self.print_summary()
        
        # Overall success check
        if s3_success and db_success and cognito_success:
            print(f"\n🎉 PURGE COMPLETED SUCCESSFULLY for user '{email}'")
        else:
            print(f"\n⚠️  PURGE COMPLETED WITH ERRORS for user '{email}'")
            print("   Please review the output above for details")


def main():
    """Main entry point for the user purge utility."""
    try:
        purge_utility = VirtualLegacyUserPurge()
        purge_utility.run_purge()
    except KeyboardInterrupt:
        print("\n\n❌ Operation cancelled by user (Ctrl+C)")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()