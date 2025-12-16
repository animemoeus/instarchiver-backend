import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from instagram.models import Post
from instagram.tasks.post import download_post_thumbnail_from_url

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Post)
def post_post_save(sender, instance, created, **kwargs):
    """
    Trigger tasks when Post is saved.
    - Downloads thumbnail if needed
    - Processes carousel media if needed (works on creation and updates)
    Uses transaction.on_commit() to ensure tasks run after DB commit.
    """
    # Only trigger if we have a thumbnail URL but no thumbnail file
    if instance.thumbnail_url and not instance.thumbnail:
        # Use transaction.on_commit to ensure the task only runs after
        # the database transaction is committed
        def queue_thumbnail_task():
            download_post_thumbnail_from_url.delay(instance.id)
            logger.info(
                "Thumbnail download task queued for post %s",
                instance.id,
            )

        transaction.on_commit(queue_thumbnail_task)

    # Carousel handling - triggers on both creation and updates
    # Safe to call multiple times due to get_or_create in _handle_post_carousel
    if instance.raw_data and instance.raw_data.get("carousel_media"):

        def queue_carousel_processing():
            instance.handle_post_carousel()
            logger.info(
                "Carousel media processed for post %s",
                instance.id,
            )

        transaction.on_commit(queue_carousel_processing)
