"""Monthly Streak Freeze Reset - EventBridge Scheduled Lambda

PURPOSE:
- Resets streakFreezeAvailable to true for all users on 1st of each month
- Ensures every user gets one freeze per month as per business rules
- Runs automatically via EventBridge cron schedule

SCHEDULE:
- Cron: 0 0 1 * ? * (midnight UTC on 1st of every month)
- Configured in template.yml MonthlyResetFunction Events

PROCESSING:
- Scans entire UserProgressDB table
- Updates only users with streakFreezeAvailable=false
- Uses batch operations for efficiency
- Logs metrics to CloudWatch for monitoring

MONITORING:
- CloudWatch metrics: MonthlyResetSuccess, MonthlyResetErrors
- Logs: Updated count and error count
- Alerts can be configured on error metrics

PERFORMANCE:
- Timeout: 300 seconds (5 minutes)
- Memory: 512 MB
- Handles pagination for large user bases
"""
import json
import boto3
from datetime import datetime

def lambda_handler(event, context):
    """Execute monthly streak freeze reset for all users."""
    
    print(f"Starting monthly streak freeze reset at {datetime.now().isoformat()}")
    
    # Initialize DynamoDB connection
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('EngagementDB')
    
    # Track processing statistics
    updated_count = 0  # Users who had freeze reset
    error_count = 0    # Failed updates
    
    try:
        # SCAN ENTIRE TABLE with pagination
        # Only fetch userId and streakFreezeAvailable to minimize data transfer
        scan_kwargs = {'ProjectionExpression': 'userId, streakFreezeAvailable'}
        
        # Process all pages of scan results
        while True:
            response = table.scan(**scan_kwargs)
            items = response.get('Items', [])
            
            # BATCH UPDATE users who need freeze reset
            # Only update users with streakFreezeAvailable=false to minimize writes
            with table.batch_writer() as batch:
                for item in items:
                    try:
                        user_id = item['userId']
                        # Only update if freeze was used (false)
                        if not item.get('streakFreezeAvailable', True):
                            batch.put_item(Item={
                                'userId': user_id,
                                'streakFreezeAvailable': True
                            })
                            updated_count += 1
                    except Exception as e:
                        print(f"Error updating user {item.get('userId')}: {e}")
                        error_count += 1
            
            # Handle pagination - continue if more results exist
            if 'LastEvaluatedKey' not in response:
                break
            scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
        
        # LOG METRICS to CloudWatch for monitoring and alerting
        cloudwatch = boto3.client('cloudwatch')
        cloudwatch.put_metric_data(
            Namespace='VirtualLegacy/Streaks',
            MetricData=[
                {'MetricName': 'MonthlyResetSuccess', 'Value': updated_count, 'Unit': 'Count'},
                {'MetricName': 'MonthlyResetErrors', 'Value': error_count, 'Unit': 'Count'}
            ]
        )
        
        print(f"Monthly reset complete: {updated_count} users updated, {error_count} errors")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Monthly reset complete',
                'usersUpdated': updated_count,
                'errors': error_count
            })
        }
        
    except Exception as e:
        print(f"Fatal error in monthly reset: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
