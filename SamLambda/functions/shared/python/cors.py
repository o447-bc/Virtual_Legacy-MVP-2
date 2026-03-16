"""
Shared CORS helpers for all Lambda functions.

ALLOWED_ORIGIN is set via the ALLOWED_ORIGIN environment variable in template.yml.
For local development, the handler checks the incoming Origin header against an
allowlist and echoes back the matching origin (required for credentialed requests).
"""
import os

_ALLOWED_ORIGINS = [
    'https://www.soulreel.net',
    'https://soulreel.net',
    'http://localhost:5173',
    'http://localhost:8080',
]

# Primary allowed origin — used when no Origin header is present
ALLOWED_ORIGIN = os.environ.get(
    'ALLOWED_ORIGIN',
    'https://www.soulreel.net'
)


def get_cors_origin(event: dict) -> str:
    """Return the echoed origin if it's in the allowlist, else the primary origin."""
    origin = (event.get('headers') or {}).get('origin', '') or \
             (event.get('headers') or {}).get('Origin', '')
    return origin if origin in _ALLOWED_ORIGINS else ALLOWED_ORIGIN


def cors_headers(event: dict = None) -> dict:
    """Return CORS headers dict. Pass the Lambda event to echo the request origin."""
    origin = get_cors_origin(event) if event else ALLOWED_ORIGIN
    return {
        'Access-Control-Allow-Origin': origin,
        'Access-Control-Allow-Headers': (
            'Content-Type,X-Amz-Date,Authorization,'
            'X-Api-Key,X-Amz-Security-Token'
        ),
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
    }

