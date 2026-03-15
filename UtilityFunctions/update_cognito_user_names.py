#!/usr/bin/env python3
"""
Update Cognito User Names Script

This script updates existing Cognito users who don't have first and last names
with generated fake names for testing purposes.

Usage:
    python3 update_cognito_user_names.py
"""

import boto3
import time
from datetime import datetime

# Configuration
USER_POOL_ID = 'us-east-1_KsG65yYlo'
REGION = 'us-east-1'

# Fake names for testing
FIRST_NAMES = [
    'John', 'Jane', 'Michael', 'Sarah', 'David',
    'Emily', 'Robert', 'Lisa', 'William', 'Jennifer',
    'James', 'Mary', 'Richard', 'Patricia', 'Thomas',
    'Linda', 'Charles', 'Barbara', 'Daniel', 'Elizabeth'
]

LAST_NAMES = [
    'Smith', 'Johnson', 'Williams', 'Brown', 'Jones',
    'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez',
    'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson',
    'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin'
]

def list_all_users(cognito_client):
    """List all users in the Cognito User Pool with pagination"""
    users = []
    pagination_token = None
    
    print(f"Fetching users from User Pool: {USER_POOL_ID}")
    
    while True:
        if pagination_token:
            response = cognito_client.list_users(
                UserPoolId=USER_POOL_ID,
                PaginationToken=pagination_token
            )
        else:
            response = cognito_client.list_users(
                UserPoolId=USER_POOL_ID
            )
        
        users.extend(response.get('Users', []))
        
        pagination_token = response.get('PaginationToken')
        if not pagination_token:
            break
    
    print(f"Found {len(users)} total users")
    return users

def get_user_attributes(user):
    """Extract user attributes into a dictionary"""
    attributes = {}
    for attr in user.get('Attributes', []):
        attributes[attr['Name']] = attr['Value']
    return attributes

def update_user_names(cognito_client, username, first_name, last_name):
    """Update user's given_name and family_name attributes"""
    try:
        cognito_client.admin_update_user_attributes(
            UserPoolId=USER_POOL_ID,
            Username=username,
            UserAttributes=[
                {'Name': 'given_name', 'Value': first_name},
                {'Name': 'family_name', 'Value': last_name}
            ]
        )
        return True
    except Exception as e:
        print(f"  ERROR updating user {username}: {str(e)}")
        return False

def main():
    """Main function to update user names"""
    print("=" * 80)
    print("Cognito User Names Update Script")
    print("=" * 80)
    print(f"Started at: {datetime.now().isoformat()}")
    print()
    
    # Initialize Cognito client
    cognito_client = boto3.client('cognito-idp', region_name=REGION)
    
    # List all users
    users = list_all_users(cognito_client)
    
    if not users:
        print("No users found in the User Pool")
        return
    
    print()
    print("Checking users for missing names...")
    print("-" * 80)
    
    users_updated = 0
    users_skipped = 0
    users_failed = 0
    
    for index, user in enumerate(users):
        username = user['Username']
        attributes = get_user_attributes(user)
        email = attributes.get('email', 'N/A')
        
        # Check if user already has names
        has_first_name = 'given_name' in attributes
        has_last_name = 'family_name' in attributes
        
        if has_first_name and has_last_name:
            print(f"[{index + 1}/{len(users)}] SKIP: {email} - Already has names: {attributes['given_name']} {attributes['family_name']}")
            users_skipped += 1
            continue
        
        # Generate fake names based on index
        first_name = FIRST_NAMES[index % len(FIRST_NAMES)]
        last_name = LAST_NAMES[index % len(LAST_NAMES)]
        
        print(f"[{index + 1}/{len(users)}] UPDATE: {email}")
        print(f"  Username: {username}")
        print(f"  Assigning: {first_name} {last_name}")
        
        # Update the user
        success = update_user_names(cognito_client, username, first_name, last_name)
        
        if success:
            print(f"  ✓ Successfully updated")
            users_updated += 1
        else:
            users_failed += 1
        
        # Rate limiting: 1 update per second to avoid throttling
        if index < len(users) - 1:  # Don't sleep after last user
            time.sleep(1)
    
    # Summary
    print()
    print("=" * 80)
    print("Update Summary")
    print("=" * 80)
    print(f"Total users:     {len(users)}")
    print(f"Updated:         {users_updated}")
    print(f"Skipped:         {users_skipped}")
    print(f"Failed:          {users_failed}")
    print(f"Completed at:    {datetime.now().isoformat()}")
    print("=" * 80)

if __name__ == '__main__':
    main()
