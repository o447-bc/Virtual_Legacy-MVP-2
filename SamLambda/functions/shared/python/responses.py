"""
Shared response helpers for all Lambda functions.

Provides safe error responses that log full details internally
but never expose exception messages to clients.
"""
import json
import os
import traceback

from cors import cors_headers

_DEFAULT_ORIGIN = os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')


def error_response(status_code: int, public_message: str, exception: Exception = None,
                   event: dict = None, log=None) -> dict:
    """
    Return a safe HTTP error response.

    - Logs the full exception traceback to CloudWatch.
    - Returns only `public_message` to the caller (no internal details).
    - When a StructuredLog instance is passed via `log`, uses structured
      JSON logging instead of print().
    """
    if exception is not None:
        if log is not None:
            log.error(public_message, exception)
        else:
            print(f"[ERROR] {public_message}: {exception}")
            print(traceback.format_exc())

    return {
        'statusCode': status_code,
        'headers': cors_headers(event),
        'body': json.dumps({'error': public_message}),
    }
