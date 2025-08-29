import logging
from typing import Any

from .core_api import make_request

logger = logging.getLogger(__name__)


def fetch_user_info_by_username_v2(username: str) -> dict[str, Any]:
    """Fetch Instagram user information by username using Core API v2 endpoint.

    Args:
        username: Instagram username to fetch information for

    Returns:
        Dictionary containing user information from the API response

    Raises:
        ImproperlyConfigured: If API settings are not configured
        requests.RequestException: If the API request fails
    """
    endpoint = "/api/v1/instagram/web_app/fetch_user_info_by_username_v2"
    params = {"username": username}

    logger.info("Fetching user info for username: %s", username)

    try:
        response = make_request("GET", endpoint, params=params)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        logger.exception("Failed to fetch user info for username %s: %s", username, e)  # noqa: TRY401
        raise
    else:
        logger.info("Successfully fetched user info for username: %s", username)
        return data
