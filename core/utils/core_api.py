import logging
from typing import Any

import requests
from django.core.exceptions import ImproperlyConfigured

from settings.models import CoreAPISetting

logger = logging.getLogger(__name__)


def get_api_url() -> str:
    """Retrieve Core API URL from settings."""
    setting = CoreAPISetting.get_solo()
    if not setting.api_url:
        msg = "Core API URL is not configured in settings"
        raise ImproperlyConfigured(msg)
    return setting.api_url


def get_api_token() -> str:
    """Retrieve Core API token from settings."""
    setting = CoreAPISetting.get_solo()
    if not setting.api_token:
        msg = "Core API token is not configured in settings"
        raise ImproperlyConfigured(msg)
    return setting.api_token


def get_core_api_session() -> requests.Session:
    """Initialize and return requests session with configured settings."""
    token = get_api_token()
    session = requests.Session()
    session.headers.update(
        {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    return session


def validate_settings() -> bool:
    """Validate Core API settings are properly configured."""
    try:
        setting = CoreAPISetting.get_solo()
        return bool(
            setting.api_url
            and setting.api_url.strip()
            and setting.api_token
            and setting.api_token.strip(),
        )
    except (AttributeError, ImportError):
        return False


def make_request(
    method: str,
    endpoint: str,
    data: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    timeout: int = 30,
) -> requests.Response:
    """Make HTTP request to Core API.

    Args:
        method: HTTP method (GET, POST, PUT, DELETE, etc.)
        endpoint: API endpoint path (without base URL)
        data: Request payload for POST/PUT requests
        params: Query parameters
        timeout: Request timeout in seconds

    Returns:
        Response object

    Raises:
        ImproperlyConfigured: If API settings are not configured
        requests.RequestException: If request fails
    """
    base_url = get_api_url().rstrip("/")
    endpoint = endpoint.lstrip("/")
    url = f"{base_url}/{endpoint}"

    session = get_core_api_session()

    try:
        response = session.request(
            method=method.upper(),
            url=url,
            json=data,
            params=params,
            timeout=timeout,
        )
        response.raise_for_status()
        return response  # noqa: TRY300
    except requests.RequestException as e:
        logger.exception("Core API request failed: %s", e)  # noqa: TRY401
        raise


def check_connection() -> bool:
    """Check if Core API connection is working."""
    try:
        response = make_request("GET", "/api/v1/health/check", timeout=10)
        response.raise_for_status()
    except Exception as e:
        logger.exception("Failed to connect to Core API: %s", e)  # noqa: TRY401
        return False
    else:
        return True
