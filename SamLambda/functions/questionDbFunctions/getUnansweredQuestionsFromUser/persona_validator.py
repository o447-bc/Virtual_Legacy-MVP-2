import json
import os

class PersonaValidator:
    """Centralized persona validation for all Lambda functions"""
    
    @staticmethod
    def get_user_persona_from_jwt(event):
        """Extract persona information from Cognito JWT token"""
        
        auth_context = event.get('requestContext', {}).get('authorizer', {})
        claims = auth_context.get('claims', {})
        
        return {
            'user_id': claims.get('sub'),
            'email': claims.get('email'),
            'persona_type': claims.get('custom:persona_type', ''),
            'initiator_id': claims.get('custom:initiator_id', ''),
            'related_user_id': claims.get('custom:related_user_id', '')
        }
    
    @staticmethod
    def validate_legacy_maker_access(persona_info):
        """Validate that user is a legacy maker who can upload/access questions"""
        
        if not persona_info['user_id']:
            return False, "No user ID found"
        
        if persona_info['persona_type'] != 'legacy_maker':
            return False, f"Only legacy makers can perform this action. Current persona: {persona_info['persona_type']}"
        
        return True, "Access granted"
    
    @staticmethod
    def validate_legacy_benefactor_access(persona_info):
        """Validate that user is a legacy benefactor who can view content"""
        
        if not persona_info['user_id']:
            return False, "No user ID found"
        
        if persona_info['persona_type'] != 'legacy_benefactor':
            return False, f"Only legacy benefactors can perform this action. Current persona: {persona_info['persona_type']}"
        
        return True, "Access granted"
    
    @staticmethod
    def create_access_denied_response(message, status_code=403):
        """Create standardized access denied response"""
        
        return {
            'statusCode': status_code,
            'headers': {
                'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net'),
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
            },
            'body': json.dumps({
                'error': message,
                'errorType': 'AccessDenied'
            })
        }
    
    @staticmethod
    def add_persona_context_to_response(response_body, persona_info):
        """Add persona context to API response for frontend use"""
        
        if isinstance(response_body, dict):
            response_body['userContext'] = {
                'persona_type': persona_info['persona_type'],
                'user_id': persona_info['user_id'],
                'is_initiator': persona_info['initiator_id'] == persona_info['user_id']
            }
        
        return response_body