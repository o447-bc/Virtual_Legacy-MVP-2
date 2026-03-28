"""
Storage Module
Handles S3 storage for conversation transcripts
"""

import json
import os
import time
import boto3
from botocore.client import Config
from decimal import Decimal
from typing import Dict

# Configure S3 client to use Signature Version 4 (required for KMS-encrypted objects)
s3 = boto3.client('s3', config=Config(signature_version='s3v4'))
dynamodb = boto3.resource('dynamodb')

BUCKET_NAME = os.environ.get('S3_BUCKET', 'virtual-legacy')
TABLE_QUESTION_STATUS = os.environ.get('TABLE_QUESTION_STATUS', 'userQuestionStatusDB')
TABLE_QUESTION_PROGRESS = os.environ.get('TABLE_QUESTION_PROGRESS', 'userQuestionLevelProgressDB')

def save_transcript_to_s3(user_id: str, question_id: str, conversation_data: Dict) -> str:
    """Save conversation transcript to S3"""
    
    key = f"conversations/{user_id}/{question_id}/transcript.json"
    
    print(f"[S3] Saving transcript to s3://{BUCKET_NAME}/{key}")
    
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=key,
        Body=json.dumps(conversation_data, indent=2),
        ContentType='application/json'
    )
    
    s3_url = f"s3://{BUCKET_NAME}/{key}"
    print(f"[S3] Transcript saved: {s3_url}")
    return s3_url

def update_question_status(user_id: str, question_id: str, transcript_url: str, 
                          final_score: float, turn_count: int):
    """Update userQuestionStatusDB with completion data"""
    
    table = dynamodb.Table(TABLE_QUESTION_STATUS)
    
    print(f"[DYNAMODB] Updating question status for user={user_id}, question={question_id}")
    
    table.put_item(Item={
        'userId': user_id,
        'questionId': question_id,
        'status': 'completed',
        'responseType': 'conversation',
        'videoType': 'audio_conversation',
        'audioTranscriptUrl': transcript_url,
        'audioConversationScore': Decimal(str(final_score)),
        'audioTurnCount': int(turn_count),
        'completedAt': int(time.time()),
        'enableTranscript': True,
        'audioSummarizationStatus': 'NOT_STARTED'
    })
    
    print("[DYNAMODB] Question status updated")

def update_user_progress(user_id: str, question_id: str, question_type: str):
    """Update userQuestionLevelProgressDB - matches video upload behavior"""
    try:
        table = dynamodb.Table(TABLE_QUESTION_PROGRESS)
        
        response = table.get_item(Key={'userId': user_id, 'questionType': question_type})
        if 'Item' not in response:
            print(f"[PROGRESS] No progress record for {question_type}")
            return
            
        item = response['Item']
        item['numQuestComplete'] = int(item.get('numQuestComplete', 0)) + 1
        
        old_ids = item.get('remainQuestAtCurrLevel', [])
        old_texts = item.get('remainQuestTextAtCurrLevel', [])
        try:
            idx = old_ids.index(question_id)
            remain_ids = old_ids[:idx] + old_ids[idx+1:]
            remain_texts = old_texts[:idx] + old_texts[idx+1:] if idx < len(old_texts) else old_texts[:]
        except ValueError:
            # question_id not in list — already removed or never present
            remain_ids = old_ids[:]
            remain_texts = old_texts[:]
            print(f"[PROGRESS] Warning: question_id {question_id} not found in remainQuestAtCurrLevel")
        
        item['remainQuestAtCurrLevel'] = remain_ids
        item['remainQuestTextAtCurrLevel'] = remain_texts
        
        table.put_item(Item=item)
        print(f"[PROGRESS] Updated {question_type}: {len(remain_ids)} remaining")
        
    except Exception as e:
        print(f"[PROGRESS] Error: {e}")

def invalidate_cache(user_id: str):
    """Invalidate SSM cache - matches video upload behavior"""
    try:
        ssm = boto3.client('ssm')
        ssm.delete_parameter(Name=f'/virtuallegacy/user_completed_count/{user_id}')
        print(f"[CACHE] Invalidated cache for {user_id}")
    except Exception as e:
        if 'ParameterNotFound' not in str(e):
            print(f"[CACHE] Error: {e}")

def trigger_summarization(user_id: str, question_id: str, conversation_data: Dict) -> Dict:
    """Trigger synchronous summarization and return summary data"""
    transcript = "\n\n".join([
        f"User: {turn['user_text']}\nAI: {turn['ai_response']}"
        for turn in conversation_data.get('turns', [])
    ])
    
    print(f"[VIDEO MEMORY] Starting summarization for {question_id}")
    print(f"[VIDEO MEMORY] Transcript length: {len(transcript)} chars")
    
    try:
        lambda_client = boto3.client('lambda')
        response = lambda_client.invoke(
            FunctionName='Virtual-Legacy-MVP-1-SummarizeTranscriptFunction-AjSfOwXjRUA9',
            InvocationType='RequestResponse',  # Synchronous call
            Payload=json.dumps({
                'userId': user_id,
                'questionId': question_id,
                'transcript': transcript,
                'videoType': 'audio_conversation'
            })
        )
        
        print(f"[VIDEO MEMORY] Lambda response status: {response.get('StatusCode')}")
        
        # Parse response
        response_payload = json.loads(response['Payload'].read())
        print(f"[VIDEO MEMORY] Response payload keys: {list(response_payload.keys())}")
        
        if response.get('StatusCode') == 200 and 'body' in response_payload:
            summary_data = json.loads(response_payload['body'])
            print(f"[VIDEO MEMORY] Summary data keys: {list(summary_data.keys())}")
            print(f"[VIDEO MEMORY] detailedSummary present: {bool(summary_data.get('detailedSummary'))}")
            print(f"[VIDEO MEMORY] detailedSummary length: {len(summary_data.get('detailedSummary', ''))}")
            print(f"[VIDEO MEMORY] detailedSummary preview: {summary_data.get('detailedSummary', '')[:200]}")
            return summary_data
        else:
            print(f"[VIDEO MEMORY] Summarization failed: {response_payload}")
            return {}
    except Exception as e:
        print(f"[VIDEO MEMORY] Error in trigger_summarization: {e}")
        import traceback
        print(f"[VIDEO MEMORY] Traceback: {traceback.format_exc()}")
        return {}
