"""
LLM Interaction Module
Handles Bedrock API calls for conversation and scoring
"""

import json
import boto3
from typing import Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

def generate_ai_response(
    question_text: str,
    conversation_history: List[Dict],
    user_response: str,
    system_prompt: str,
    model_id: str
) -> str:
    """Generate AI interviewer response using Claude"""
    
    # Build conversation context
    messages = []
    for turn in conversation_history:
        messages.append({
            "role": "user",
            "content": turn['user_text']
        })
        messages.append({
            "role": "assistant",
            "content": turn['ai_response']
        })
    
    # Add current user response
    messages.append({
        "role": "user",
        "content": user_response
    })
    
    # Prepare request
    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 500,
        "temperature": 0.7,
        "system": system_prompt.format(question=question_text),
        "messages": messages
    }
    
    print(f"[LLM] Calling Bedrock with model: {model_id}")
    print(f"[LLM] Message count: {len(messages)}")
    
    response = bedrock.invoke_model(
        modelId=model_id,
        body=json.dumps(request_body)
    )
    
    response_body = json.loads(response['body'].read())
    ai_text = response_body['content'][0]['text']
    
    print(f"[LLM] Response length: {len(ai_text)} characters")
    return ai_text

def score_response_depth(
    user_response: str,
    scoring_prompt: str,
    model_id: str
) -> Tuple[float, str]:
    """Score the depth of user's response using Claude"""
    
    messages = [{
        "role": "user",
        "content": f"{scoring_prompt}\n\nUser response to score:\n{user_response}"
    }]
    
    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 300,
        "temperature": 0.3,
        "messages": messages
    }
    
    print(f"[SCORING] Calling Bedrock with model: {model_id}")
    
    response = bedrock.invoke_model(
        modelId=model_id,
        body=json.dumps(request_body)
    )
    
    response_body = json.loads(response['body'].read())
    score_text = response_body['content'][0]['text']
    
    # Parse score and reasoning
    try:
        score_text = score_text.strip()
        
        # Check if response is just a number
        try:
            score = float(score_text)
            print(f"[SCORING] Score: {score} (direct number)")
            return score, "Score provided without reasoning"
        except ValueError:
            pass
        
        # Expected format: "Score: X.X\nReasoning: ..."
        lines = score_text.split('\n')
        score_line = [l for l in lines if l.startswith('Score:')][0]
        score = float(score_line.split(':')[1].strip())
        
        reasoning_lines = [l for l in lines if not l.startswith('Score:')]
        reasoning = '\n'.join(reasoning_lines).replace('Reasoning:', '').strip()
        
        print(f"[SCORING] Score: {score}, Reasoning length: {len(reasoning)}")
        return score, reasoning
    except Exception as e:
        print(f"[SCORING] Error parsing score: {e}")
        print(f"[SCORING] Raw response: {score_text}")
        return 1.0, "Unable to parse score"

def process_user_response_parallel(
    question_text: str,
    conversation_history: List[Dict],
    user_response: str,
    system_prompt: str,
    scoring_prompt: str,
    conversation_model_id: str,
    scoring_model_id: str
) -> Tuple[str, float, str]:
    """Process user response with parallel scoring and AI generation"""
    
    print(f"[PARALLEL] Starting parallel LLM calls")
    
    with ThreadPoolExecutor(max_workers=2) as executor:
        # Submit both tasks simultaneously
        score_future = executor.submit(
            score_response_depth,
            user_response,
            scoring_prompt,
            scoring_model_id
        )
        
        response_future = executor.submit(
            generate_ai_response,
            question_text,
            conversation_history,
            user_response,
            system_prompt,
            conversation_model_id
        )
        
        # Wait for both to complete
        ai_response = response_future.result()
        turn_score, reasoning = score_future.result()
    
    print(f"[PARALLEL] Both calls completed")
    return ai_response, turn_score, reasoning
