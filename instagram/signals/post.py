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
    - Processes post based on type (normal, carousel, or video)
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

    # Post type handling - triggers on both creation and updates
    # Safe to call multiple times due to get_or_create in handler methods
    if instance.raw_data:

        def queue_post_processing():
            instance.process_post_by_type()
            logger.info(
                "Post processing completed for post %s (variant: %s)",
                instance.id,
                instance.variant,
            )

        transaction.on_commit(queue_post_processing)
