"""
Referral hash and unsubscribe token utilities for the email capture nurture system.
"""
import hashlib
import hmac
import base64


def generate_referral_hash(email: str, salt: str) -> str:
    """
    Generate a short, non-reversible hash of an email address for referral tracking.
    
    Returns the first 10 characters of a SHA-256 hash of the email+salt.
    Deterministic: same email+salt always produces the same hash.
    """
    return hashlib.sha256(f"{email.lower()}:{salt}".encode()).hexdigest()[:10]


def generate_unsubscribe_token(email: str, secret: str) -> str:
    """
    Generate an HMAC-signed unsubscribe token for an email address.
    
    The token contains the email and its HMAC signature, base64url-encoded.
    Can be verified with verify_unsubscribe_token().
    """
    sig = hmac.new(
        secret.encode(), email.lower().encode(), hashlib.sha256
    ).digest()
    payload = f"{email.lower()}:{sig.hex()}"
    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip('=')


def verify_unsubscribe_token(token: str, secret: str) -> str | None:
    """
    Verify an unsubscribe token and extract the email address.
    
    Returns the email address if the token is valid, None if tampered or invalid.
    """
    try:
        # Add padding back for base64 decoding
        padded = token + '=' * (4 - len(token) % 4)
        decoded = base64.urlsafe_b64decode(padded).decode()
        email, sig_hex = decoded.rsplit(':', 1)
        expected = hmac.new(
            secret.encode(), email.encode(), hashlib.sha256
        ).hexdigest()
        if hmac.compare_digest(sig_hex, expected):
            return email
        return None
    except Exception:
        return None
