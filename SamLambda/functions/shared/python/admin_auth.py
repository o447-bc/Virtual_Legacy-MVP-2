"""
Admin authorization helper for SoulReelAdmins group verification.

Used by all admin Lambda functions as a server-side defense-in-depth check
on top of the API Gateway CognitoAuthorizer.
"""

ADMIN_GROUP = 'SoulReelAdmins'


def verify_admin(event):
    """
    Extract user info from JWT claims and verify SoulReelAdmins group membership.

    The CognitoAuthorizer on API Gateway validates the JWT token. This function
    performs an additional server-side check that the caller belongs to the
    SoulReelAdmins Cognito group.

    Args:
        event: The Lambda event dict from API Gateway

    Returns:
        tuple (email, sub) if the user is a verified admin, or None if not.
        - email: the user's email from the JWT 'email' claim
        - sub: the user's unique ID from the JWT 'sub' claim
    """
    claims = (
        event.get('requestContext', {})
        .get('authorizer', {})
        .get('claims', {})
    )

    if not claims:
        return None

    # cognito:groups comes as a comma-separated string from API Gateway
    # e.g., "SoulReelAdmins,AnotherGroup" or just "SoulReelAdmins"
    # If the user is in no groups, the claim may be absent entirely.
    groups_str = claims.get('cognito:groups', '')
    groups = [g.strip() for g in groups_str.split(',') if g.strip()]

    if ADMIN_GROUP not in groups:
        return None

    email = claims.get('email', 'unknown')
    sub = claims.get('sub', '')

    return (email, sub)
