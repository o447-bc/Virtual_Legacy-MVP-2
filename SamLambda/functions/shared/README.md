# Shared Persona Validator

This module provides centralized persona validation for all Lambda functions in the Virtual Legacy application.

## Usage

### 1. Import the PersonaValidator

```python
import sys
import os

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))
from persona_validator import PersonaValidator
```

### 2. Extract Persona Information from JWT

```python
def lambda_handler(event, context):
    # Extract persona info from Cognito JWT token
    persona_info = PersonaValidator.get_user_persona_from_jwt(event)
    
    # persona_info contains:
    # - user_id: Cognito User ID
    # - email: User's email
    # - persona_type: 'legacy_maker' or 'legacy_benefactor'
    # - initiator_id: ID of the user who pays for the service
    # - related_user_id: ID of related user (if any)
```

### 3. Validate Access Based on Persona

```python
# For functions that only legacy makers should access (questions, video upload)
is_valid, message = PersonaValidator.validate_legacy_maker_access(persona_info)

if not is_valid:
    return PersonaValidator.create_access_denied_response(message)

# For functions that only legacy benefactors should access (video viewing - future)
is_valid, message = PersonaValidator.validate_legacy_benefactor_access(persona_info)

if not is_valid:
    return PersonaValidator.create_access_denied_response(message)
```

### 4. Add Persona Context to Responses

```python
# Add user context to response for frontend use
response_body = {
    'data': 'your_data_here'
}

response_body = PersonaValidator.add_persona_context_to_response(response_body, persona_info)

# Response now includes:
# {
#   'data': 'your_data_here',
#   'userContext': {
#     'persona_type': 'legacy_maker',
#     'user_id': 'user-123',
#     'is_initiator': true
#   }
# }
```

## Methods

### `get_user_persona_from_jwt(event)`
Extracts persona information from Cognito JWT token in the Lambda event.

### `validate_legacy_maker_access(persona_info)`
Returns `(True, "Access granted")` if user is a legacy maker, `(False, error_message)` otherwise.

### `validate_legacy_benefactor_access(persona_info)`
Returns `(True, "Access granted")` if user is a legacy benefactor, `(False, error_message)` otherwise.

### `create_access_denied_response(message, status_code=403)`
Creates a standardized HTTP 403 response with CORS headers.

### `add_persona_context_to_response(response_body, persona_info)`
Adds user context information to the response body for frontend use.

## Testing

Run the test suite:
```bash
python test_persona_validator.py
```