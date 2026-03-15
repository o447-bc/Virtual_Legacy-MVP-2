#!/bin/bash
# Setup SSM parameters for LLM prompts

echo "Creating SSM parameters for LLM prompts..."

aws ssm put-parameter \
  --name "/life-story-app/llm-prompts/combined-prompt" \
  --value "You are an empathetic life story curator analyzing personal video transcripts.

Your task: Analyze this transcript and provide THREE outputs in JSON format:

1. oneSentence: ONE sentence capturing the core experiences, values, and essence
2. detailedSummary: 5-10 sentences highlighting pivotal moments, reflections, and emotional depth
3. thoughtfulnessScore: Integer 0-5 rating depth (0=no content, 1=minimal, 2=some reflection, 3=moderate, 4=thoughtful, 5=profoundly insightful)

Preserve authentic voice and emotional nuance. Focus on what matters most to them.

Transcript:
{transcript}

Respond ONLY with valid JSON:
{\"oneSentence\": \"...\", \"detailedSummary\": \"...\", \"thoughtfulnessScore\": 3}" \
  --type String \
  --overwrite \
  --region us-east-1

aws ssm put-parameter \
  --name "/life-story-app/llm-prompts/model-id" \
  --value "anthropic.claude-3-haiku-20240307-v1:0" \
  --type String \
  --overwrite \
  --region us-east-1

echo "✅ SSM parameters created successfully"
echo ""
echo "To verify, run:"
echo "aws ssm get-parameter --name /life-story-app/llm-prompts/model-id --region us-east-1"
