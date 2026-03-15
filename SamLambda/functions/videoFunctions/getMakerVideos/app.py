import os
import json
import boto3
from botocore.client import Config
from decimal import Decimal
from botocore.exceptions import ClientError
from cors import cors_headers
from responses import error_response


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)

def lambda_handler(event, context):
    # CORS preflight - EXACT COPY from incrementUserLevel2
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net'),
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': ''
        }
    
    # Extract authenticated benefactor ID - EXACT COPY from incrementUserLevel2
    benefactor_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub')
    if not benefactor_id:
        return {
            'statusCode': 401,
            'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
            'body': json.dumps({'error': 'Unauthorized'})
        }
    
    try:
        # Extract makerId from path
        maker_id = event['pathParameters']['makerId']
        
        dynamodb = boto3.resource('dynamodb')
        # Configure S3 client to use Signature Version 4 (required for KMS-encrypted objects)
        s3_client = boto3.client('s3', config=Config(signature_version='s3v4'))
        
        # Validate relationship exists - check both directions
        rel_table = dynamodb.Table(os.environ.get('TABLE_RELATIONSHIPS', 'PersonaRelationshipsDB'))
        
        # Direction 1: benefactor initiated (legacy invite flow)
        rel_response = rel_table.get_item(
            Key={'initiator_id': benefactor_id, 'related_user_id': maker_id}
        )
        
        authorized = 'Item' in rel_response and rel_response['Item'].get('status') == 'active'
        
        # Direction 2: maker initiated assignment flow (maker→benefactor)
        if not authorized:
            rel_response2 = rel_table.get_item(
                Key={'initiator_id': maker_id, 'related_user_id': benefactor_id}
            )
            authorized = 'Item' in rel_response2 and rel_response2['Item'].get('status') == 'active'
        
        if not authorized:
            return {
                'statusCode': 403,
                'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
                'body': json.dumps({'error': 'Unauthorized access'})
            }
        
        # Query videos
        video_table = dynamodb.Table(os.environ.get('TABLE_QUESTION_STATUS', 'userQuestionStatusDB'))
        video_response = video_table.query(
            KeyConditionExpression='userId = :uid',
            ExpressionAttributeValues={':uid': maker_id}
        )
        
        videos = video_response.get('Items', [])
        
        if not videos:
            return {
                'statusCode': 200,
                'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
                'body': json.dumps({})
            }
        
        # Generate presigned URLs and group by type
        grouped = {}
        
        for item in videos:
            q_type = item.get('questionType', 'Unknown')
            if not q_type:
                continue
            
            if q_type not in grouped:
                grouped[q_type] = {'friendlyName': q_type, 'videos': []}
            
            # Determine response type and extract data
            video_s3_location = item.get('videoS3Location', '')
            video_memory_s3_location = item.get('videoMemoryS3Location', '')
            audio_one_sentence = item.get('audioOneSentence', '')
            video_one_sentence = item.get('videoOneSentence', '')
            video_memory_one_sentence = item.get('videoMemoryOneSentence', '')
            
            response_type = None
            video_url = None
            thumbnail_url = None
            one_sentence = None
            
            # Determine timestamp based on response type
            timestamp = None
            
            # Check for video memory first
            if video_memory_s3_location:
                response_type = 'video_memory'
                s3_key = video_memory_s3_location.replace('s3://virtual-legacy/', '')
                try:
                    video_url = s3_client.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': 'virtual-legacy', 'Key': s3_key},
                        ExpiresIn=10800
                    )
                    thumbnail_key = s3_key.replace('.webm', '.jpg')
                    thumbnail_url = s3_client.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': 'virtual-legacy', 'Key': thumbnail_key},
                        ExpiresIn=10800
                    )
                except:
                    pass
                one_sentence = video_memory_one_sentence if video_memory_one_sentence else None
                timestamp = item.get('videoMemoryTimestamp', '')
            
            # Check for regular video
            elif video_s3_location:
                response_type = 'video'
                s3_key = video_s3_location.replace('s3://virtual-legacy/', '')
                try:
                    video_url = s3_client.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': 'virtual-legacy', 'Key': s3_key},
                        ExpiresIn=10800
                    )
                    thumbnail_key = s3_key.replace('.webm', '.jpg')
                    thumbnail_url = s3_client.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': 'virtual-legacy', 'Key': thumbnail_key},
                        ExpiresIn=10800
                    )
                except:
                    pass
                one_sentence = video_one_sentence if video_one_sentence else None
                timestamp = item.get('timestamp', '')
            
            # Check for audio response
            elif audio_one_sentence:
                response_type = 'audio'
                one_sentence = audio_one_sentence
                # Convert Unix timestamp to ISO string
                completed_at = item.get('completedAt')
                if completed_at:
                    from datetime import datetime
                    timestamp = datetime.fromtimestamp(int(completed_at)).isoformat()
                else:
                    timestamp = item.get('summarizationCompletedAt', '')
            
            # Skip if no valid response type found
            if not response_type:
                continue
            
            # Convert empty string to None
            if one_sentence == '':
                one_sentence = None
            
            # Generate presigned URL for audio recording
            audio_url = None
            if response_type == 'audio':
                audio_transcript_s3 = item.get('audioTranscriptUrl', '')
                if audio_transcript_s3:
                    # Extract base path and look for audio files
                    base_path = audio_transcript_s3.replace('s3://virtual-legacy/', '').replace('/transcript.json', '')
                    audio_folder = f"{base_path}/audio/"
                    try:
                        # List audio files in the folder
                        list_response = s3_client.list_objects_v2(
                            Bucket='virtual-legacy',
                            Prefix=audio_folder,
                            MaxKeys=1
                        )
                        if 'Contents' in list_response and len(list_response['Contents']) > 0:
                            audio_key = list_response['Contents'][0]['Key']
                            audio_url = s3_client.generate_presigned_url(
                                'get_object',
                                Params={'Bucket': 'virtual-legacy', 'Key': audio_key},
                                ExpiresIn=10800
                            )
                    except Exception as e:
                        print(f"Error generating audio URL: {e}")
            
            grouped[q_type]['videos'].append({
                'questionId': item['questionId'],
                'questionType': q_type,
                'questionText': item.get('Question', ''),
                'responseType': response_type,
                'videoUrl': video_url,
                'thumbnailUrl': thumbnail_url,
                'audioUrl': audio_url,
                'oneSentence': one_sentence,
                'timestamp': timestamp or '',
                'filename': item.get('filename', '')
            })
        
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
            'body': json.dumps(grouped, cls=DecimalEncoder)
        }
        
    except Exception as e:
        print(f"Error in getMakerVideos: {e}")
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
            'body': json.dumps({'error': 'A server error occurred. Please try again.'})
        }
