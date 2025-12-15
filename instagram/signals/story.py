import logging
import uuid

from django.core.files.base import ContentFile
from django.db.models.signals import post_save
from django.dispatch import receiver

from instagram.models import Story
from instagram.utils import download_file_from_url

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Story)
def download_story_media(sender, instance, created, **kwargs):
    """Download media files from URLs when Story is saved."""
    updated = False

    # Download thumbnail if URL exists but file field is empty
    if instance.thumbnail_url and not instance.thumbnail:
        content, extension = download_file_from_url(instance.thumbnail_url)
        if content and extension:
            filename = f"{uuid.uuid4()}.{extension}"
            instance.thumbnail.save(filename, ContentFile(content), save=False)
            updated = True
            logger.info("Downloaded thumbnail for story %s", instance.story_id)

    # Download media if URL exists but file field is empty
    if instance.media_url and not instance.media:
        content, extension = download_file_from_url(instance.media_url)
        if content and extension:
            filename = f"{uuid.uuid4()}.{extension}"
            instance.media.save(filename, ContentFile(content), save=False)
            updated = True
            logger.info("Downloaded media for story %s", instance.story_id)

    # Save instance if any files were downloaded (avoid infinite loop)
    if updated:
        instance.save()
