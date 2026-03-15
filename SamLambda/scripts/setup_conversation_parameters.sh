#!/bin/bash
# Setup SSM Parameters for Audio Conversation Feature
# Run this script to create all required configuration parameters

REGION="us-east-1"

echo "🚀 Setting up conversation parameters in SSM Parameter Store..."

# Score goal
aws ssm put-parameter \
  --name "/virtuallegacy/conversation/score-goal" \
  --value "12" \
  --type "String" \
  --description "Target cumulative score to end conversation" \
  --region $REGION \
  --overwrite 2>/dev/null || \
aws ssm put-parameter \
  --name "/virtuallegacy/conversation/score-goal" \
  --value "12" \
  --type "String" \
  --description "Target cumulative score to end conversation" \
  --region $REGION

echo "✅ Created: score-goal = 12"

# Max turns
aws ssm put-parameter \
  --name "/virtuallegacy/conversation/max-turns" \
  --value "20" \
  --type "String" \
  --description "Maximum conversation turns (safety limit)" \
  --region $REGION \
  --overwrite 2>/dev/null || \
aws ssm put-parameter \
  --name "/virtuallegacy/conversation/max-turns" \
  --value "20" \
  --type "String" \
  --description "Maximum conversation turns (safety limit)" \
  --region $REGION

echo "✅ Created: max-turns = 20"

# LLM conversation model
aws ssm put-parameter \
  --name "/virtuallegacy/conversation/llm-conversation-model" \
  --value "anthropic.claude-3-5-sonnet-20241022-v2:0" \
  --type "String" \
  --description "Bedrock model for conversation generation" \
  --region $REGION \
  --overwrite 2>/dev/null || \
aws ssm put-parameter \
  --name "/virtuallegacy/conversation/llm-conversation-model" \
  --value "anthropic.claude-3-5-sonnet-20241022-v2:0" \
  --type "String" \
  --description "Bedrock model for conversation generation" \
  --region $REGION

echo "✅ Created: llm-conversation-model = Claude 3.5 Sonnet v2"

# LLM scoring model
aws ssm put-parameter \
  --name "/virtuallegacy/conversation/llm-scoring-model" \
  --value "anthropic.claude-3-haiku-20240307-v1:0" \
  --type "String" \
  --description "Bedrock model for response scoring" \
  --region $REGION \
  --overwrite 2>/dev/null || \
aws ssm put-parameter \
  --name "/virtuallegacy/conversation/llm-scoring-model" \
  --value "anthropic.claude-3-haiku-20240307-v1:0" \
  --type "String" \
  --description "Bedrock model for response scoring" \
  --region $REGION

echo "✅ Created: llm-scoring-model = Claude 3 Haiku"

# System prompt
aws ssm put-parameter \
  --name "/virtuallegacy/conversation/system-prompt" \
  --value "You are an empathetic interviewer helping someone share their life story. Ask thoughtful follow-up questions that encourage deeper reflection. Build on previous responses. Show genuine curiosity. Encourage specific examples and emotions. Keep questions concise (1-2 sentences)." \
  --type "String" \
  --description "System prompt for conversation LLM" \
  --region $REGION \
  --overwrite 2>/dev/null || \
aws ssm put-parameter \
  --name "/virtuallegacy/conversation/system-prompt" \
  --value "You are an empathetic interviewer helping someone share their life story. Ask thoughtful follow-up questions that encourage deeper reflection. Build on previous responses. Show genuine curiosity. Encourage specific examples and emotions. Keep questions concise (1-2 sentences)." \
  --type "String" \
  --description "System prompt for conversation LLM" \
  --region $REGION

echo "✅ Created: system-prompt"

# Scoring prompt
aws ssm put-parameter \
  --name "/virtuallegacy/conversation/scoring-prompt" \
  --value "Score the user's response for depth on a scale of 0-5. 0: No response or irrelevant. 1: Superficial or one-word answer. 2: Basic facts without reflection. 3: Some personal insight or examples. 4: Detailed reflection with emotions or lessons. 5: Profound, introspective sharing with vulnerability. Output only the integer score." \
  --type "String" \
  --description "Prompt for scoring response depth" \
  --region $REGION \
  --overwrite 2>/dev/null || \
aws ssm put-parameter \
  --name "/virtuallegacy/conversation/scoring-prompt" \
  --value "Score the user's response for depth on a scale of 0-5. 0: No response or irrelevant. 1: Superficial or one-word answer. 2: Basic facts without reflection. 3: Some personal insight or examples. 4: Detailed reflection with emotions or lessons. 5: Profound, introspective sharing with vulnerability. Output only the integer score." \
  --type "String" \
  --description "Prompt for scoring response depth" \
  --region $REGION

echo "✅ Created: scoring-prompt"

# Polly voice
aws ssm put-parameter \
  --name "/virtuallegacy/conversation/polly-voice-id" \
  --value "Joanna" \
  --type "String" \
  --description "Amazon Polly voice ID" \
  --region $REGION \
  --overwrite 2>/dev/null || \
aws ssm put-parameter \
  --name "/virtuallegacy/conversation/polly-voice-id" \
  --value "Joanna" \
  --type "String" \
  --description "Amazon Polly voice ID" \
  --region $REGION

echo "✅ Created: polly-voice-id = Joanna"

# Polly engine
aws ssm put-parameter \
  --name "/virtuallegacy/conversation/polly-engine" \
  --value "neural" \
  --type "String" \
  --description "Amazon Polly engine (neural or standard)" \
  --region $REGION \
  --overwrite 2>/dev/null || \
aws ssm put-parameter \
  --name "/virtuallegacy/conversation/polly-engine" \
  --value "neural" \
  --type "String" \
  --description "Amazon Polly engine (neural or standard)" \
  --region $REGION

echo "✅ Created: polly-engine = neural"

echo ""
echo "🎉 All conversation parameters created successfully!"
echo ""
echo "To view parameters:"
echo "  aws ssm get-parameters-by-path --path /virtuallegacy/conversation/ --region us-east-1"
echo ""
echo "To update a parameter:"
echo "  aws ssm put-parameter --name /virtuallegacy/conversation/score-goal --value 15 --overwrite --region us-east-1"
