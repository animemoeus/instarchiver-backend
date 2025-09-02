import json
import sys
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


def _ensure_firebase_initialized():
    """Ensure Firebase app is initialized before use."""
    global _firebase_app_initialized  # noqa: PLW0603

    if _firebase_app_initialized:
        return

    # Check if default app already exists
    try:
        firebase_admin.get_app()
        _firebase_app_initialized = True
        return  # noqa: TRY300
    except ValueError:
        # Default app doesn't exist, proceed with initialization
        pass

    # Check if we're in test environment
    is_testing = "pytest" in sys.modules

    if is_testing:
        # For tests, try to initialize if settings exist, otherwise skip
        try:
            cred = _get_firebase_credentials()
            firebase_admin.initialize_app(cred)
            _firebase_app_initialized = True
        except (ImproperlyConfigured, FileNotFoundError):
            # Silently skip Firebase initialization in test environment
            pass
    else:
        # In non-test environments, credentials must be properly configured
        cred = _get_firebase_credentials()
        firebase_admin.initialize_app(cred)
        _firebase_app_initialized = True


# Firebase app will be initialized lazily when needed
_firebase_app_initialized = False


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
    _ensure_firebase_initialized()
    try:
        return auth.verify_id_token(token)
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
    _ensure_firebase_initialized()
    decoded_token = auth.verify_id_token(token)
    uid = decoded_token["uid"]
    user = auth.get_user(uid)

    return {
        "uid": user.uid,
        "email": user.email,
        "name": user.display_name or "",
        "photo_url": user.photo_url,
    }
