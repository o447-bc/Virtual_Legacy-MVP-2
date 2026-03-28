import json
import os
import boto3
from botocore.client import Config
import traceback
import time

from conversation_state import ConversationState, get_conversation, set_conversation, remove_conversation
from config import get_conversation_config
from llm import process_user_response_parallel, generate_ai_response, score_response_depth
from speech import text_to_speech
from storage import (save_transcript_to_s3, update_question_status, 
                     update_user_progress, invalidate_cache, trigger_summarization)
from transcribe import transcribe_audio
from transcribe_streaming import transcribe_audio_streaming
from transcribe_deepgram import transcribe_audio_deepgram

apigateway = None  # Initialized lazily in lambda_handler (endpoint URL comes from env at runtime)
# Configure S3 client to use Signature Version 4 (required for KMS-encrypted objects)
s3_client = boto3.client('s3', config=Config(signature_version='s3v4'))

S3_BUCKET = os.environ.get('S3_BUCKET', 'virtual-legacy')

def send_message(connection_id: str, message: dict):
    """Send message to WebSocket client"""
    try:
        if message.get('type') in ['conversation_complete', 'conversation_ended']:
            print(f"[SEND] Sending {message.get('type')} with keys: {list(message.keys())}")
            print(f"[SEND] audioDetailedSummary present: {bool(message.get('audioDetailedSummary'))}")
            print(f"[SEND] audioDetailedSummary length: {len(message.get('audioDetailedSummary', ''))}")
        apigateway.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(message).encode('utf-8')
        )
        print(f"[SEND] Message sent: {message.get('type')}")
    except Exception as e:
        print(f"[SEND] Error: {e}")
        raise

def handle_start_conversation(connection_id: str, user_id: str, body: dict, config: dict):
    """Handle start_conversation action"""
    question_id = body.get('questionId')
    question_text = body.get('questionText')
    
    if not question_id or not question_text:
        send_message(connection_id, {
            'type': 'error',
            'message': 'Missing questionId or questionText'
        })
        return
    
    print(f"[START] Starting conversation for question: {question_id}")
    
    # Create conversation state
    state = ConversationState(connection_id, user_id, question_id, question_text)
    set_conversation(connection_id, state)
    
    # Send initial greeting
    greeting = question_text
    
    try:
        audio_url = text_to_speech(greeting, user_id, question_id, 0, config['polly_voice_id'], config['polly_engine'])
        
        send_message(connection_id, {
            'type': 'ai_speaking',
            'text': greeting,
            'audioUrl': audio_url,
            'turnNumber': 0,
            'cumulativeScore': 0,
            'scoreGoal': config['score_goal']
        })
    except Exception as e:
        print(f"[START] Error generating speech: {e}")
        send_message(connection_id, {
            'type': 'ai_speaking',
            'text': greeting,
            'turnNumber': 0,
            'cumulativeScore': 0,
            'scoreGoal': config['score_goal']
        })

def handle_user_response(connection_id: str, user_id: str, body: dict, config: dict):
    """Handle user_response action"""
    user_text = body.get('text')
    
    if not user_text:
        send_message(connection_id, {
            'type': 'error',
            'message': 'Missing text in user response'
        })
        return
    
    # Get conversation state
    state = get_conversation(connection_id)
    if not state:
        send_message(connection_id, {
            'type': 'error',
            'message': 'No active conversation. Start with start_conversation action.'
        })
        return
    
    print(f"[RESPONSE] Processing user response: {len(user_text)} characters")
    
    try:
        # Score and generate AI response in parallel
        ai_response, turn_score, reasoning = process_user_response_parallel(
            state.question_text,
            state.turns,
            user_text,
            config['system_prompt'],
            config['scoring_prompt'],
            config['llm_conversation_model'],
            config['llm_scoring_model']
        )

        # Add turn to state and persist
        state.add_turn(user_text, ai_response, turn_score, reasoning)
        set_conversation(connection_id, state)
        
        # Send score update
        send_message(connection_id, {
            'type': 'score_update',
            'turnScore': turn_score,
            'cumulativeScore': state.cumulative_score,
            'scoreGoal': config['score_goal'],
            'turnNumber': state.turn_number,
            'reasoning': reasoning
        })
        
        # Check if conversation should continue
        should_continue, reason = state.should_continue(
            config['score_goal'],
            config['max_turns']
        )
        
        if not should_continue:
            # Conversation complete
            state.completed = True
            state.completion_reason = reason
            
            # Save transcript
            transcript_url = save_transcript_to_s3(
                user_id,
                state.question_id,
                state.to_dict()
            )
            
            # Update question status
            update_question_status(
                user_id,
                state.question_id,
                transcript_url,
                state.cumulative_score,
                state.turn_number
            )
            
            # Update progress
            question_type = state.question_id.rsplit('-', 1)[0]
            update_user_progress(user_id, state.question_id, question_type)
            invalidate_cache(user_id)
            summary_data = trigger_summarization(user_id, state.question_id, state.to_dict())
            detailed_summary = summary_data.get('detailedSummary', '')
            print(f"[VIDEO MEMORY] Text response - summary length: {len(detailed_summary)}")
            
            # Send completion message
            send_message(connection_id, {
                'type': 'conversation_complete',
                'finalScore': state.cumulative_score,
                'totalTurns': state.turn_number,
                'audioTranscriptUrl': transcript_url,
                'reason': reason,
                'audioDetailedSummary': detailed_summary
            })
            print(f"[VIDEO MEMORY] Sent conversation_complete with audioDetailedSummary: {bool(detailed_summary)}")
            
            # Clean up
            remove_conversation(connection_id)
            return
        
        # Generate speech for AI response
        try:
            audio_url = text_to_speech(ai_response, user_id, state.question_id, state.turn_number, config['polly_voice_id'], config['polly_engine'])
            
            send_message(connection_id, {
                'type': 'ai_speaking',
                'text': ai_response,
                'audioUrl': audio_url,
                'turnNumber': state.turn_number,
                'cumulativeScore': state.cumulative_score
            })
        except Exception as e:
            print(f"[RESPONSE] Error generating speech: {e}")
            send_message(connection_id, {
                'type': 'ai_speaking',
                'text': ai_response,
                'turnNumber': state.turn_number,
                'cumulativeScore': state.cumulative_score
            })
            
    except Exception as e:
        print(f"[RESPONSE] Error processing response: {e}")
        print(traceback.format_exc())
        send_message(connection_id, {
            'type': 'error',
            'message': 'Error processing response. Please try again.'
        })

def handle_audio_response(connection_id: str, user_id: str, body: dict, config: dict):
    """Handle audio_response action - transcribe audio then process as user response"""
    s3_key = body.get('s3Key')
    
    if not s3_key:
        send_message(connection_id, {
            'type': 'error',
            'message': 'Missing s3Key in audio_response'
        })
        return
    
    # Get conversation state
    state = get_conversation(connection_id)
    if not state:
        send_message(connection_id, {
            'type': 'error',
            'message': 'No active conversation. Start with start_conversation action.'
        })
        return
    
    print(f"[AUDIO] Processing audio from S3: {s3_key}")
    
    try:
        # Three-tier fallback: Deepgram (fastest) → AWS Streaming → AWS Batch
        transcribe_start = time.time()
        
        try:
            # Tier 1: Deepgram (0.5s average)
            print(f"[AUDIO] Attempting Deepgram transcription")
            result = transcribe_audio_deepgram(
                s3_key,
                user_id,
                state.question_id,
                state.turn_number + 1
            )
            transcribe_time = time.time() - transcribe_start
            print(f"[AUDIO] Deepgram transcription successful in {transcribe_time:.2f}s")
            
        except Exception as deepgram_error:
            print(f"[AUDIO] Deepgram failed: {deepgram_error}")
            
            try:
                # Tier 2: AWS Streaming (5s average)
                print(f"[AUDIO] Falling back to AWS Streaming transcription")
                streaming_start = time.time()
                result = transcribe_audio_streaming(
                    s3_key,
                    user_id,
                    state.question_id,
                    state.turn_number + 1
                )
                streaming_time = time.time() - streaming_start
                print(f"[AUDIO] AWS Streaming transcription successful in {streaming_time:.2f}s")
                
            except Exception as streaming_error:
                print(f"[AUDIO] AWS Streaming failed: {streaming_error}")
                
                # Tier 3: AWS Batch (15s average, most reliable)
                print(f"[AUDIO] Falling back to AWS Batch transcription")
                batch_start = time.time()
                result = transcribe_audio(
                    s3_key,
                    user_id,
                    state.question_id,
                    state.turn_number + 1
                )
                batch_time = time.time() - batch_start
                print(f"[AUDIO] AWS Batch transcription successful in {batch_time:.2f}s")
        
        user_text = result['transcript']
        audio_url = result['audio_url']
        
        print(f"[AUDIO] Transcribed: {user_text}")
        print(f"[AUDIO] Audio stored: {audio_url}")
        
        # Validate transcription is not empty
        if not user_text or not user_text.strip():
            print(f"[AUDIO] Empty transcription detected - audio may be too short or silent")
            send_message(connection_id, {
                'type': 'error',
                'message': 'No speech detected. Please speak clearly and try again.'
            })
            return
        
        # Process with parallel scoring and response generation
        ai_response, turn_score, reasoning = process_user_response_parallel(
            state.question_text,
            state.turns,
            user_text,
            config['system_prompt'],
            config['scoring_prompt'],
            config['llm_conversation_model'],
            config['llm_scoring_model']
        )
        
        # Add turn to state (with audio URL) and persist
        state.add_turn(user_text, ai_response, turn_score, reasoning)
        # Store audio URL in turn metadata
        if state.turns:
            state.turns[-1]['audio_url'] = audio_url
        set_conversation(connection_id, state)
        
        # Send score update
        send_message(connection_id, {
            'type': 'score_update',
            'turnScore': turn_score,
            'cumulativeScore': state.cumulative_score,
            'scoreGoal': config['score_goal'],
            'turnNumber': state.turn_number,
            'reasoning': reasoning
        })
        
        # Check if conversation should continue
        should_continue, reason = state.should_continue(
            config['score_goal'],
            config['max_turns']
        )
        
        if not should_continue:
            # Conversation complete
            state.completed = True
            state.completion_reason = reason
            
            # Save transcript
            transcript_url = save_transcript_to_s3(
                user_id,
                state.question_id,
                state.to_dict()
            )
            
            # Update question status
            update_question_status(
                user_id,
                state.question_id,
                transcript_url,
                state.cumulative_score,
                state.turn_number
            )
            
            # Update progress
            question_type = state.question_id.rsplit('-', 1)[0]
            update_user_progress(user_id, state.question_id, question_type)
            invalidate_cache(user_id)
            summary_data = trigger_summarization(user_id, state.question_id, state.to_dict())
            detailed_summary = summary_data.get('detailedSummary', '')
            print(f"[VIDEO MEMORY] Summary data received: {summary_data}")
            print(f"[VIDEO MEMORY] Detailed summary length: {len(detailed_summary)}")
            print(f"[VIDEO MEMORY] Detailed summary preview: {detailed_summary[:200] if detailed_summary else 'EMPTY'}")
            
            # Send completion message
            send_message(connection_id, {
                'type': 'conversation_complete',
                'finalScore': state.cumulative_score,
                'totalTurns': state.turn_number,
                'audioTranscriptUrl': transcript_url,
                'reason': reason,
                'audioDetailedSummary': detailed_summary
            })
            print(f"[VIDEO MEMORY] Sent conversation_complete with audioDetailedSummary: {bool(detailed_summary)}")
            
            # Clean up
            remove_conversation(connection_id)
            return
        
        # Generate speech for AI response
        try:
            audio_url = text_to_speech(ai_response, user_id, state.question_id, state.turn_number, config['polly_voice_id'], config['polly_engine'])
            
            send_message(connection_id, {
                'type': 'ai_speaking',
                'text': ai_response,
                'audioUrl': audio_url,
                'turnNumber': state.turn_number,
                'cumulativeScore': state.cumulative_score
            })
        except Exception as e:
            print(f"[AUDIO] Error generating speech: {e}")
            send_message(connection_id, {
                'type': 'ai_speaking',
                'text': ai_response,
                'turnNumber': state.turn_number,
                'cumulativeScore': state.cumulative_score
            })
            
    except Exception as e:
        print(f"[AUDIO] Error processing audio: {e}")
        print(traceback.format_exc())
        send_message(connection_id, {
            'type': 'error',
            'message': 'Error processing audio. Please try again.'
        })

def handle_get_upload_url(connection_id: str, user_id: str):
    """Handle get_upload_url action - generate presigned S3 URL for audio upload"""
    state = get_conversation(connection_id)
    if not state:
        send_message(connection_id, {
            'type': 'error',
            'message': 'No active conversation. Start with start_conversation action.'
        })
        return
    
    print(f"[UPLOAD_URL] Generating presigned URL for user {user_id}, turn {state.turn_number + 1}")
    
    try:
        from datetime import datetime
        timestamp = int(datetime.now().timestamp())
        next_turn = state.turn_number + 1
        s3_key = f"conversations/{user_id}/{state.question_id}/audio/turn-{next_turn}-{timestamp}.webm"
        
        # Get KMS key ARN from environment
        kms_key_arn = os.environ.get('KMS_KEY_ARN')
        
        # Log request parameters for debugging
        print(f"[UPLOAD_URL] User: {user_id}")
        print(f"[UPLOAD_URL] Question: {state.question_id}")
        print(f"[UPLOAD_URL] S3 Key: {s3_key}")
        print(f"[UPLOAD_URL] Bucket: {S3_BUCKET}")
        print(f"[UPLOAD_URL] KMS Key: {kms_key_arn}")
        print(f"[UPLOAD_URL] Expiration: 900 seconds (15 minutes)")
        
        # Generate presigned URL WITHOUT KMS parameters
        # The bucket has default encryption configured, so S3 will automatically
        # apply KMS encryption to all uploads. Including KMS params in the presigned URL
        # would require the client to send x-amz-server-side-encryption headers,
        # which browsers cannot do in a simple PUT request.
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': S3_BUCKET,
                'Key': s3_key
                # ServerSideEncryption and SSEKMSKeyId intentionally omitted
                # Bucket default encryption will apply KMS automatically
            },
            ExpiresIn=900  # 15 minutes
        )
        
        print(f"[UPLOAD_URL] URL generated successfully (signature valid for 15 min)")
        print(f"[UPLOAD_URL] S3 key path includes user ID for security: {user_id in s3_key}")
        
        send_message(connection_id, {
            'type': 'upload_url',
            'uploadUrl': presigned_url,
            's3Key': s3_key
        })
        
    except boto3.exceptions.Boto3Error as e:
        error_msg = f"S3 client error: {str(e)}"
        print(f"[UPLOAD_URL] {error_msg}")
        print(f"[UPLOAD_URL] Error type: {type(e).__name__}")
        print(traceback.format_exc())
        send_message(connection_id, {
            'type': 'error',
            'message': f'Failed to generate upload URL. Please try again. ({type(e).__name__})'
        })
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(f"[UPLOAD_URL] {error_msg}")
        print(f"[UPLOAD_URL] Error type: {type(e).__name__}")
        print(traceback.format_exc())
        send_message(connection_id, {
            'type': 'error',
            'message': f'Error generating upload URL. Please try again.'
        })

def handle_end_conversation(connection_id: str, user_id: str):
    """Handle end_conversation action"""
    state = get_conversation(connection_id)
    if state:
        print(f"[END] Ending conversation early: {state.turn_number} turns")
        
        # Save partial transcript
        try:
            transcript_url = save_transcript_to_s3(
                user_id,
                state.question_id,
                state.to_dict()
            )
            
            # Update question status and progress — same as natural completion path
            update_question_status(
                user_id,
                state.question_id,
                transcript_url,
                state.cumulative_score,
                state.turn_number
            )
            question_type = state.question_id.rsplit('-', 1)[0]
            update_user_progress(user_id, state.question_id, question_type)
            invalidate_cache(user_id)
            
            summary_data = trigger_summarization(user_id, state.question_id, state.to_dict())
            detailed_summary = summary_data.get('detailedSummary', '')
            print(f"[VIDEO MEMORY] End conversation - summary length: {len(detailed_summary)}")
            
            send_message(connection_id, {
                'type': 'conversation_ended',
                'finalScore': state.cumulative_score,
                'totalTurns': state.turn_number,
                'audioTranscriptUrl': transcript_url,
                'audioDetailedSummary': detailed_summary
            })
            print(f"[VIDEO MEMORY] Sent conversation_ended with audioDetailedSummary: {bool(detailed_summary)}")
        except Exception as e:
            print(f"[END] Error saving transcript: {e}")
        
        remove_conversation(connection_id)
    else:
        send_message(connection_id, {
            'type': 'error',
            'message': 'No active conversation to end'
        })

def lambda_handler(event, context):
    global apigateway
    if apigateway is None:
        apigateway = boto3.client('apigatewaymanagementapi',
            endpoint_url=f"https://{os.environ['WEBSOCKET_API_ENDPOINT']}")

    print(f"[HANDLER] Event: {json.dumps(event)}")
    
    connection_id = event['requestContext']['connectionId']
    user_id = event['requestContext'].get('authorizer', {}).get('userId', 'unknown')
    
    print(f"[HANDLER] Connection: {connection_id}, User: {user_id}")
    
    try:
        body = json.loads(event.get('body', '{}'))
        action = body.get('action')
        
        print(f"[HANDLER] Action: {action}")
        
        # Load configuration
        config = get_conversation_config()
        
        # Route to appropriate handler
        if action == 'start_conversation':
            handle_start_conversation(connection_id, user_id, body, config)
        elif action == 'user_response':
            handle_user_response(connection_id, user_id, body, config)
        elif action == 'get_upload_url':
            handle_get_upload_url(connection_id, user_id)
        elif action == 'audio_response':
            handle_audio_response(connection_id, user_id, body, config)
        elif action == 'end_conversation':
            handle_end_conversation(connection_id, user_id)
        else:
            send_message(connection_id, {
                'type': 'error',
                'message': f'Unknown action: {action}'
            })
        
        return {'statusCode': 200, 'body': 'Success'}
        
    except Exception as e:
        print(f"[HANDLER] Fatal error: {e}")
        print(traceback.format_exc())
        
        try:
            send_message(connection_id, {
                'type': 'error',
                'message': 'A server error occurred. Please try again.'
            })
        except:
            pass
        
        return {'statusCode': 500, 'body': 'Error'}
