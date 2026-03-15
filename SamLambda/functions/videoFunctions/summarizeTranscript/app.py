import json
import boto3
import os
from datetime import datetime, timedelta

bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb')
ssm_client = boto3.client('ssm')
cloudwatch = boto3.client('cloudwatch')

_ssm_cache = {}
_cache_ttl = timedelta(minutes=5)

def get_ssm_parameter(param_name):
    """Fetch SSM parameter with caching."""
    now = datetime.now()
    
    if param_name in _ssm_cache:
        value, timestamp = _ssm_cache[param_name]
        if now - timestamp < _cache_ttl:
            return value
    
    response = ssm_client.get_parameter(Name=param_name)
    value = response['Parameter']['Value']
    _ssm_cache[param_name] = (value, now)
    return value

def lambda_handler(event, context):
    """Triggered when transcript completed. Generates LLM summary and score."""
    try:
        # Parse input
        if 'Records' in event:
            record = event['Records'][0]
            bucket = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
            
            parts = key.split('/')
            if len(parts) < 3 or not key.endswith('.txt'):
                print(f"Skipping non-transcript file: {key}")
                return {'statusCode': 200}
            
            user_id = parts[1]
            filename = parts[2]
            question_id = filename.split('_')[0]
            
            s3_client = boto3.client('s3')
            obj = s3_client.get_object(Bucket=bucket, Key=key)
            transcript = obj['Body'].read().decode('utf-8')
            video_type = event.get('videoType', 'regular_video')
        else:
            user_id = event['userId']
            question_id = event['questionId']
            transcript = event['transcript']
            video_type = event.get('videoType', 'regular_video')
        
        print(f"Processing summarization for {user_id}/{question_id}")
        
        if is_already_summarized(user_id, question_id):
            print(f"Already summarized, skipping: {user_id}/{question_id}")
            return {'statusCode': 200, 'body': 'Already summarized'}
        
        if not check_enable_transcript_flag(user_id, question_id):
            print(f"Summarization disabled for {user_id}/{question_id}")
            emit_metric('SummarizationSkipped', 1)
            return {'statusCode': 200, 'body': 'Summarization disabled'}
        
        if not transcript or len(transcript.strip()) < 10:
            print(f"Transcript too short: {len(transcript)} chars")
            update_summarization_status(user_id, question_id, 'FAILED', 
                                       error='Transcript too short or empty')
            return {'statusCode': 200, 'body': 'Transcript too short'}
        
        MAX_TRANSCRIPT_LENGTH = 100000
        if len(transcript) > MAX_TRANSCRIPT_LENGTH:
            print(f"Truncating transcript from {len(transcript)} to {MAX_TRANSCRIPT_LENGTH} chars")
            transcript = transcript[:MAX_TRANSCRIPT_LENGTH] + "..."
        
        update_summarization_status(user_id, question_id, 'IN_PROGRESS')
        
        prompt_template = get_ssm_parameter('/life-story-app/llm-prompts/combined-prompt')
        model_id = get_ssm_parameter('/life-story-app/llm-prompts/model-id')
        
        prompt = prompt_template.replace('{transcript}', transcript)
        
        start_time = datetime.now()
        result = invoke_bedrock(model_id, prompt)
        processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        summary_data = parse_bedrock_response(result)
        
        update_summarization_results(user_id, question_id, summary_data, video_type)
        
        emit_metric('SummarizationCompleted', 1)
        emit_metric('ProcessingTimeMs', processing_time_ms)
        
        print(f"✅ Summarization completed for {user_id}/{question_id}")
        return {'statusCode': 200, 'body': json.dumps(summary_data)}
        
    except Exception as e:
        print(f"❌ Error in summarization: {str(e)}")
        emit_metric('SummarizationFailed', 1)
        
        if 'user_id' in locals() and 'question_id' in locals():
            update_summarization_status(user_id, question_id, 'FAILED', error=str(e))
        
        raise

def is_already_summarized(user_id, question_id):
    """Check if already summarized (idempotency)."""
    try:
        table = dynamodb.Table(os.environ.get('TABLE_QUESTION_STATUS', 'userQuestionStatusDB'))
        response = table.get_item(Key={'userId': user_id, 'questionId': question_id})
        
        if 'Item' in response:
            item = response['Item']
            if item.get('summarizationStatus') == 'COMPLETED':
                return True
        return False
    except Exception as e:
        print(f"Error checking summarization status: {e}")
        return False

def check_enable_transcript_flag(user_id, question_id):
    """Check if summarization enabled."""
    try:
        table = dynamodb.Table(os.environ.get('TABLE_QUESTION_STATUS', 'userQuestionStatusDB'))
        response = table.get_item(Key={'userId': user_id, 'questionId': question_id})
        
        if 'Item' not in response:
            return True
        
        item = response['Item']
        return item.get('enableTranscript', True)
        
    except Exception as e:
        print(f"Error checking enableTranscript flag: {e}")
        return True

def invoke_bedrock(model_id, prompt):
    """Call Amazon Bedrock with Claude model."""
    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 2048,
        "temperature": 0.7,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }
    
    response = bedrock_runtime.invoke_model(
        modelId=model_id,
        body=json.dumps(request_body)
    )
    
    response_body = json.loads(response['body'].read())
    return response_body

def parse_bedrock_response(bedrock_response):
    """Extract and parse JSON from Bedrock response."""
    content = bedrock_response['content'][0]['text']
    
    import re
    json_match = re.search(r'\{.*\}', content, re.DOTALL)
    if not json_match:
        raise ValueError(f"No JSON found in response: {content}")
    
    json_str = json_match.group(0)
    data = json.loads(json_str)
    
    required_fields = ['oneSentence', 'detailedSummary', 'thoughtfulnessScore']
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")
    
    score = int(data['thoughtfulnessScore'])
    if score < 0 or score > 5:
        raise ValueError(f"Invalid score: {score} (must be 0-5)")
    
    return {
        'oneSentence': data['oneSentence'],
        'detailedSummary': data['detailedSummary'],
        'thoughtfulnessScore': score
    }

def update_summarization_status(user_id, question_id, status, error=None):
    """Update DynamoDB with summarization status."""
    table = dynamodb.Table(os.environ.get('TABLE_QUESTION_STATUS', 'userQuestionStatusDB'))
    
    update_expr = 'SET summarizationStatus = :status, summarizationUpdatedAt = :timestamp'
    expr_values = {
        ':status': status,
        ':timestamp': datetime.now().isoformat()
    }
    
    if error:
        update_expr += ', summarizationError = :error'
        expr_values[':error'] = error
    
    table.update_item(
        Key={'userId': user_id, 'questionId': question_id},
        UpdateExpression=update_expr,
        ExpressionAttributeValues=expr_values
    )

def update_summarization_results(user_id, question_id, summary_data, video_type='regular_video'):
    """Update DynamoDB with summarization results."""
    table = dynamodb.Table(os.environ.get('TABLE_QUESTION_STATUS', 'userQuestionStatusDB'))
    
    # Determine field names based on video type
    if video_type == 'audio_conversation':
        prefix = 'audio'
    elif video_type == 'video_memory':
        prefix = 'videoMemory'
    else:  # regular_video
        prefix = 'video'
    
    table.update_item(
        Key={'userId': user_id, 'questionId': question_id},
        UpdateExpression=f'''
            SET {prefix}OneSentence = :one,
                {prefix}DetailedSummary = :detailed,
                {prefix}ThoughtfulnessScore = :score,
                {prefix}SummarizationStatus = :status,
                {prefix}SummarizationCompletedAt = :timestamp
        ''',
        ExpressionAttributeValues={
            ':one': summary_data['oneSentence'],
            ':detailed': summary_data['detailedSummary'],
            ':score': summary_data['thoughtfulnessScore'],
            ':status': 'COMPLETED',
            ':timestamp': datetime.now().isoformat()
        }
    )

def emit_metric(metric_name, value):
    """Emit CloudWatch metric."""
    try:
        cloudwatch.put_metric_data(
            Namespace='VirtualLegacy/Summarization',
            MetricData=[{
                'MetricName': metric_name,
                'Value': value,
                'Unit': 'Count' if 'Count' in metric_name or 'Completed' in metric_name or 'Failed' in metric_name else 'Milliseconds',
                'Timestamp': datetime.now()
            }]
        )
    except Exception as e:
        print(f"Error emitting metric {metric_name}: {e}")
