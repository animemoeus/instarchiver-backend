import hashlib
import logging

import requests
from celery import shared_task
from django.core.files.base import ContentFile

from .models import User

logger = logging.getLogger(__name__)


@shared_task
def update_profile_picture_from_url(user_id):
    """
    Update user's profile picture from Instagram URL if content has changed.
    Uses hash comparison to detect actual image content changes.
    """
    try:
        user = User.objects.get(uuid=user_id)
    except User.DoesNotExist:
        logger.exception("User with ID %s not found", user_id)
        return {"success": False, "error": "User not found"}

    if not user.original_profile_picture_url:
        logger.info("No original profile picture URL for user %s", user.username)
        return {"success": False, "error": "No original profile picture URL"}

    try:
        # Download image from Instagram URL
        response = requests.get(user.original_profile_picture_url, timeout=30)
        response.raise_for_status()

        # Calculate hash of downloaded image content
        new_image_content = response.content
        new_image_hash = hashlib.sha256(new_image_content).hexdigest()

        # Get hash of existing profile picture if it exists
        existing_image_hash = None
        if user.profile_picture and hasattr(user.profile_picture, "file"):
            try:
                user.profile_picture.file.seek(0)
                existing_content = user.profile_picture.file.read()
                existing_image_hash = hashlib.sha256(existing_content).hexdigest()
                user.profile_picture.file.seek(0)  # Reset file pointer
            except OSError as e:
                logger.warning(
                    "Could not read existing profile picture for %s: %s",
                    user.username,
                    e,
                )

        # Compare hashes - only update if different
        if existing_image_hash == new_image_hash:
            logger.info("Profile picture unchanged for user %s", user.username)
            return {"success": True, "message": "No changes detected"}

        # Save new image
        # Extract filename from URL or use default
        filename = f"{user.username}_profile.jpg"

        # Save the new image
        user.profile_picture.save(
            filename,
            ContentFile(new_image_content),
            save=False,  # Don't save model yet to avoid triggering signal again
        )

        # Save the user model (this will trigger the signal, but we'll handle that)
        user.save(update_fields=["profile_picture"])

        logger.info("Profile picture updated for user %s", user.username)
        return {  # noqa: TRY300
            "success": True,
            "message": "Profile picture updated",
            "old_hash": existing_image_hash,
            "new_hash": new_image_hash,
        }

    except requests.RequestException as e:
        logger.exception("Failed to download profile picture for %s", user.username)
        return {"success": False, "error": f"Download failed: {e!s}"}

    except Exception as e:
        logger.exception(
            "Unexpected error updating profile picture for %s",
            user.username,
        )
        return {"success": False, "error": f"Unexpected error: {e!s}"}
