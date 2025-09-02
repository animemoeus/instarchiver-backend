import json
from typing import Any

import firebase_admin
from django.core.exceptions import ImproperlyConfigured
from firebase_admin import auth
from firebase_admin import credentials


def _get_firebase_credentials():
    """Get Firebase credentials from database settings."""
    try:
        from settings.models import FirebaseAdminSetting  # noqa: PLC0415
    except ImportError as e:
        msg = "FirebaseAdminSetting model not found"
        raise ImproperlyConfigured(msg) from e

    try:
        firebase_settings = FirebaseAdminSetting.get_solo()
    except Exception as e:
        msg = "Cannot access Firebase settings"
        raise ImproperlyConfigured(msg) from e

    if firebase_settings.service_account_json:
        try:
            service_account_data = json.loads(firebase_settings.service_account_json)
            return credentials.Certificate(service_account_data)
        except (json.JSONDecodeError, ValueError) as e:
            msg = "Invalid Firebase service account JSON content"
            raise ImproperlyConfigured(msg) from e

    msg = "Firebase service account JSON content not configured"
    raise ImproperlyConfigured(msg)


def _get_firebase_app():
    """Get Firebase app with real-time configuration from database."""
    # Get credentials from database - will raise ImproperlyConfigured if not available
    cred = _get_firebase_credentials()

    # Try to get existing default app first
    try:
        app = firebase_admin.get_app()
        # Delete existing app to reload with fresh configuration
        firebase_admin.delete_app(app)
    except ValueError:
        # No existing app, proceed with creating new one
        pass

    # Initialize with fresh credentials from database
    return firebase_admin.initialize_app(cred)


def validate_token(token: str) -> dict[str, Any]:
    """
    Validate and decode a Firebase authentication token.

    This function verifies the validity of a Firebase ID token and returns
    the decoded payload.

    Args:
        token (str): The Firebase ID token to validate.

    Returns:
        dict: The decoded token payload containing user information like
        UID, email, etc.

    Raises:
        Exception: If the token is invalid or verification fails.
    """
    app = _get_firebase_app()
    try:
        return auth.verify_id_token(token, app=app)
    except Exception as e:
        msg = "Invalid token"
        raise Exception(msg) from e  # noqa: TRY002


def get_user_info(token: str) -> dict[str, Any]:
    """
    Retrieves user information from a Firebase authentication token.

    This function verifies the provided token, extracts the user ID (uid),
    fetches the user information from Firebase, and formats the user's details.

    Args:
        token (str): The Firebase authentication token to verify.

    Returns:
        dict: A dictionary containing the user's information with the following keys:
            - uid (str): The user's unique identifier.
            - email (str): The user's email address.
            - name (str): The user's full name from display_name.
            - photo_url (str): The URL to the user's profile photo.

    Raises:
        Exception: If the token is invalid or there's an issue with
        Firebase authentication.
    """
    app = _get_firebase_app()
    decoded_token = auth.verify_id_token(token, app=app)
    uid = decoded_token["uid"]
    user = auth.get_user(uid, app=app)

    return {
        "uid": user.uid,
        "email": user.email,
        "name": user.display_name or "",
        "photo_url": user.photo_url,
    }
