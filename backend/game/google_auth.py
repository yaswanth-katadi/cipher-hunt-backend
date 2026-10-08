from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed

from google.auth.transport.requests import Request
from google.oauth2 import id_token


def verify_google_credential(credential):
    """
    Verify a Google ID token and return trusted Google account information.
    """

    if not credential or not isinstance(credential, str):
        raise AuthenticationFailed("Google credential is required.")

    if not settings.GOOGLE_CLIENT_ID:
        raise AuthenticationFailed("Google authentication is not configured.")

    try:
        idinfo = id_token.verify_oauth2_token(
            credential,
            Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except ValueError:
        raise AuthenticationFailed("Invalid Google credential.")

    issuer = idinfo.get("iss")

    if issuer not in (
        "accounts.google.com",
        "https://accounts.google.com",
    ):
        raise AuthenticationFailed("Invalid Google token issuer.")

    if not idinfo.get("email_verified"):
        raise AuthenticationFailed("Google email is not verified.")

    google_sub = idinfo.get("sub")
    email = idinfo.get("email")
    participant_name = idinfo.get("name")

    if not google_sub:
        raise AuthenticationFailed("Google account ID is missing.")

    if not email:
        raise AuthenticationFailed("Google email is missing.")

    if not participant_name:
        raise AuthenticationFailed("Google account name is missing.")

    return {
        "google_sub": google_sub,
        "email": email.lower(),
        "participant_name": participant_name,
    }