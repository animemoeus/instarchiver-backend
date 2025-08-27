import logging

import openai
from django.core.exceptions import ImproperlyConfigured

from settings.models import OpenAISetting

logger = logging.getLogger(__name__)


def get_api_key() -> str:
    """Retrieve OpenAI API key from settings."""
    setting = OpenAISetting.get_solo()
    if not setting.api_key:
        msg = "OpenAI API key is not configured in settings"
        raise ImproperlyConfigured(msg)
    return setting.api_key


def get_model_name() -> str:
    """Retrieve OpenAI model name from settings."""
    setting = OpenAISetting.get_solo()
    return setting.model_name


def get_openai_client(model_name: str | None = None) -> openai.OpenAI:
    """Initialize and return OpenAI client with configured settings.

    Args:
        model_name: Override the default model name from settings
    """
    api_key = get_api_key()
    if model_name is None:
        model_name = get_model_name()
    return openai.OpenAI(api_key=api_key)


def validate_settings() -> bool:
    """Validate OpenAI settings are properly configured."""
    try:
        setting = OpenAISetting.get_solo()
        return bool(setting.api_key and setting.api_key.strip())
    except (AttributeError, ImportError):
        return False


def check_connection() -> bool:
    """Check if OpenAI API connection is working."""
    try:
        client = get_openai_client()
        client.models.list()
    except Exception as e:
        logger.exception("Failed to connect to OpenAI API: %s", e)  # noqa: TRY401
        return False
    else:
        return True
