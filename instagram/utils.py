import logging
from urllib.parse import urlparse

import requests
from rest_framework import status

logger = logging.getLogger(__name__)


def download_file_from_url(url, timeout=30):
    """Download file from URL and return content with extension."""
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == status.HTTP_200_OK:
            # Extract file extension from URL
            parsed_url = urlparse(url)
            path = parsed_url.path
            if "." in path:
                extension = path.split(".")[-1].lower()
            else:
                # Try to determine from content type
                content_type = response.headers.get("content-type", "")
                if "image" in content_type:
                    extension = "jpg"
                elif "video" in content_type:
                    extension = "mp4"
                else:
                    extension = "bin"

            return response.content, extension
        logger.warning(
            "Failed to download file from %s: HTTP %s",
            url,
            response.status_code,
        )
        return None, None  # noqa: TRY300
    except Exception as e:
        logger.exception("Error downloading file from %s: %s", url, str(e))  # noqa: TRY401
        return None, None
