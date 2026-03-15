#!/usr/bin/env python3
"""
Rename DynamoDB fields to use prefixed naming convention:
- Audio conversation fields: audio* prefix
- Regular video fields: video* prefix  
- Video memory fields: videoMemory* prefix
"""

import boto3
from decimal import Decimal
from botocore.exceptions import ClientError

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

# Table name - unified table for all question responses
QUESTION_STATUS_TABLE = 'userQuestionStatusDB'

def rename_question_status_fields():
    """Rename fields in userQuestionStatusDB table"""
    table = dynamodb.Table(QUESTION_STATUS_TABLE)
    
    print(f"\n=== Processing {QUESTION_STATUS_TABLE} ===")
    
    # Scan all items
    response = table.scan()
    items = response['Items']
    
    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response['Items'])
    
    print(f"Found {len(items)} items to process")
    
    updated_count = 0
    error_count = 0
    
    for item in items:
        try:
            user_id = item['userId']
            question_id = item['questionId']
            response_type = item.get('responseType', 'video')
            video_type = item.get('videoType', 'regular_video')
            
            update_expr_parts = []
            expr_attr_names = {}
            expr_attr_values = {}
            remove_expr_parts = []
            
            # Determine prefix based on responseType and videoType
            if response_type == 'conversation':
                # Audio conversation fields
                if 'transcriptUrl' in item:
                    update_expr_parts.append('#atu = :atu')
                    expr_attr_names['#atu'] = 'audioTranscriptUrl'
                    expr_attr_values[':atu'] = item['transcriptUrl']
                    remove_expr_parts.append('transcriptUrl')
                
                if 'oneSentence' in item:
                    update_expr_parts.append('#aos = :aos')
                    expr_attr_names['#aos'] = 'audioOneSentence'
                    expr_attr_values[':aos'] = item['oneSentence']
                    remove_expr_parts.append('oneSentence')
                
                if 'detailedSummary' in item:
                    update_expr_parts.append('#ads = :ads')
                    expr_attr_names['#ads'] = 'audioDetailedSummary'
                    expr_attr_values[':ads'] = item['detailedSummary']
                    remove_expr_parts.append('detailedSummary')
                
                if 'thoughtfulnessScore' in item:
                    update_expr_parts.append('#acs = :acs')
                    expr_attr_names['#acs'] = 'audioConversationScore'
                    expr_attr_values[':acs'] = item['thoughtfulnessScore']
                    remove_expr_parts.append('thoughtfulnessScore')
                
                if 'turnCount' in item:
                    update_expr_parts.append('#atc = :atc')
                    expr_attr_names['#atc'] = 'audioTurnCount'
                    expr_attr_values[':atc'] = item['turnCount']
                    remove_expr_parts.append('turnCount')
                
                if 'summarizationStatus' in item:
                    update_expr_parts.append('#ass = :ass')
                    expr_attr_names['#ass'] = 'audioSummarizationStatus'
                    expr_attr_values[':ass'] = item['summarizationStatus']
                    remove_expr_parts.append('summarizationStatus')
                
                # Add videoType if not present
                if 'videoType' not in item:
                    update_expr_parts.append('#vt = :vt')
                    expr_attr_names['#vt'] = 'videoType'
                    expr_attr_values[':vt'] = 'audio_conversation'
            
            elif video_type == 'video_memory':
                # Video memory fields
                if 's3Location' in item:
                    update_expr_parts.append('#vms3 = :vms3')
                    expr_attr_names['#vms3'] = 'videoMemoryS3Location'
                    expr_attr_values[':vms3'] = item['s3Location']
                    remove_expr_parts.append('s3Location')
                
                if 'thumbnailS3Location' in item:
                    update_expr_parts.append('#vmthumb = :vmthumb')
                    expr_attr_names['#vmthumb'] = 'videoMemoryThumbnailS3Location'
                    expr_attr_values[':vmthumb'] = item['thumbnailS3Location']
                    remove_expr_parts.append('thumbnailS3Location')
                
                if 'transcriptionStatus' in item:
                    update_expr_parts.append('#vmts = :vmts')
                    expr_attr_names['#vmts'] = 'videoMemoryTranscriptionStatus'
                    expr_attr_values[':vmts'] = item['transcriptionStatus']
                    remove_expr_parts.append('transcriptionStatus')
                
                if 'transcript' in item:
                    update_expr_parts.append('#vmt = :vmt')
                    expr_attr_names['#vmt'] = 'videoMemoryTranscript'
                    expr_attr_values[':vmt'] = item['transcript']
                    remove_expr_parts.append('transcript')
                
                if 'transcriptS3Location' in item:
                    update_expr_parts.append('#vmts3 = :vmts3')
                    expr_attr_names['#vmts3'] = 'videoMemoryTranscriptS3Location'
                    expr_attr_values[':vmts3'] = item['transcriptS3Location']
                    remove_expr_parts.append('transcriptS3Location')
                
                if 'transcriptTextS3Location' in item:
                    update_expr_parts.append('#vmtts3 = :vmtts3')
                    expr_attr_names['#vmtts3'] = 'videoMemoryTranscriptTextS3Location'
                    expr_attr_values[':vmtts3'] = item['transcriptTextS3Location']
                    remove_expr_parts.append('transcriptTextS3Location')
                
                if 'oneSentence' in item:
                    update_expr_parts.append('#vmos = :vmos')
                    expr_attr_names['#vmos'] = 'videoMemoryOneSentence'
                    expr_attr_values[':vmos'] = item['oneSentence']
                    remove_expr_parts.append('oneSentence')
                
                if 'detailedSummary' in item:
                    update_expr_parts.append('#vmds = :vmds')
                    expr_attr_names['#vmds'] = 'videoMemoryDetailedSummary'
                    expr_attr_values[':vmds'] = item['detailedSummary']
                    remove_expr_parts.append('detailedSummary')
                
                if 'summarizationStatus' in item:
                    update_expr_parts.append('#vmss = :vmss')
                    expr_attr_names['#vmss'] = 'videoMemorySummarizationStatus'
                    expr_attr_values[':vmss'] = item['summarizationStatus']
                    remove_expr_parts.append('summarizationStatus')
            
            else:
                # Regular video fields
                if 's3Location' in item:
                    update_expr_parts.append('#vs3 = :vs3')
                    expr_attr_names['#vs3'] = 'videoS3Location'
                    expr_attr_values[':vs3'] = item['s3Location']
                    remove_expr_parts.append('s3Location')
                
                if 'thumbnailS3Location' in item:
                    update_expr_parts.append('#vthumb = :vthumb')
                    expr_attr_names['#vthumb'] = 'videoThumbnailS3Location'
                    expr_attr_values[':vthumb'] = item['thumbnailS3Location']
                    remove_expr_parts.append('thumbnailS3Location')
                
                if 'transcriptionStatus' in item:
                    update_expr_parts.append('#vts = :vts')
                    expr_attr_names['#vts'] = 'videoTranscriptionStatus'
                    expr_attr_values[':vts'] = item['transcriptionStatus']
                    remove_expr_parts.append('transcriptionStatus')
                
                if 'transcript' in item:
                    update_expr_parts.append('#vt = :vt')
                    expr_attr_names['#vt'] = 'videoTranscript'
                    expr_attr_values[':vt'] = item['transcript']
                    remove_expr_parts.append('transcript')
                
                if 'transcriptS3Location' in item:
                    update_expr_parts.append('#vts3 = :vts3')
                    expr_attr_names['#vts3'] = 'videoTranscriptS3Location'
                    expr_attr_values[':vts3'] = item['transcriptS3Location']
                    remove_expr_parts.append('transcriptS3Location')
                
                if 'transcriptTextS3Location' in item:
                    update_expr_parts.append('#vtts3 = :vtts3')
                    expr_attr_names['#vtts3'] = 'videoTranscriptTextS3Location'
                    expr_attr_values[':vtts3'] = item['transcriptTextS3Location']
                    remove_expr_parts.append('transcriptTextS3Location')
                
                if 'oneSentence' in item:
                    update_expr_parts.append('#vos = :vos')
                    expr_attr_names['#vos'] = 'videoOneSentence'
                    expr_attr_values[':vos'] = item['oneSentence']
                    remove_expr_parts.append('oneSentence')
                
                if 'detailedSummary' in item:
                    update_expr_parts.append('#vds = :vds')
                    expr_attr_names['#vds'] = 'videoDetailedSummary'
                    expr_attr_values[':vds'] = item['detailedSummary']
                    remove_expr_parts.append('detailedSummary')
                
                if 'summarizationStatus' in item:
                    update_expr_parts.append('#vss = :vss')
                    expr_attr_names['#vss'] = 'videoSummarizationStatus'
                    expr_attr_values[':vss'] = item['summarizationStatus']
                    remove_expr_parts.append('summarizationStatus')
            
            # Only update if there are fields to rename
            if update_expr_parts or remove_expr_parts:
                update_expr = ''
                if update_expr_parts:
                    update_expr = 'SET ' + ', '.join(update_expr_parts)
                if remove_expr_parts:
                    if update_expr:
                        update_expr += ' '
                    update_expr += 'REMOVE ' + ', '.join(remove_expr_parts)
                
                update_kwargs = {
                    'Key': {'userId': user_id, 'questionId': question_id},
                    'UpdateExpression': update_expr
                }
                
                if expr_attr_names:
                    update_kwargs['ExpressionAttributeNames'] = expr_attr_names
                if expr_attr_values:
                    update_kwargs['ExpressionAttributeValues'] = expr_attr_values
                
                table.update_item(**update_kwargs)
                updated_count += 1
                if response_type == 'conversation':
                    print(f"Updated: {user_id}/{question_id} (audio_conversation)")
                else:
                    print(f"Updated: {user_id}/{question_id} ({video_type})")
        
        except Exception as e:
            error_count += 1
            print(f"Error updating {item.get('userId')}/{item.get('questionId')}: {str(e)}")
    
    print(f"\n{QUESTION_STATUS_TABLE} Summary:")
    print(f"  Updated: {updated_count}")
    print(f"  Errors: {error_count}")
    print(f"  Skipped: {len(items) - updated_count - error_count}")


def main():
    print("=" * 60)
    print("DynamoDB Field Renaming Script")
    print("=" * 60)
    print("\nThis script will rename fields to use prefixed naming:")
    print("  - Audio conversations: audio* prefix")
    print("  - Regular videos: video* prefix")
    print("  - Video memories: videoMemory* prefix")
    print("\nPress Ctrl+C to cancel, or Enter to continue...")
    
    try:
        input()
    except KeyboardInterrupt:
        print("\n\nCancelled by user")
        return
    
    try:
        rename_question_status_fields()
        
        print("\n" + "=" * 60)
        print("Field renaming complete!")
        print("=" * 60)
    
    except Exception as e:
        print(f"\n\nFatal error: {str(e)}")
        raise


if __name__ == '__main__':
    main()
