import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from instagram.models import PostMedia
from instagram.tasks.post import download_post_media_thumbnail_from_url

logger = logging.getLogger(__name__)


@receiver(post_save, sender=PostMedia)
def post_media_post_save(sender, instance, created, **kwargs):
    """
    Trigger thumbnail download task when PostMedia is saved.
    Only triggers if thumbnail_url is present and thumbnail field is empty.
    Uses transaction.on_commit() to ensure task runs after DB commit.
    """
    # Only trigger if we have a thumbnail URL but no thumbnail file
    if instance.thumbnail_url and not instance.thumbnail:
        # Use transaction.on_commit to ensure the task only runs after
        # the database transaction is committed
        def queue_task():
            download_post_media_thumbnail_from_url.delay(instance.id)
            logger.info(
                "Thumbnail download task queued for post media %s",
                instance.id,
            )

        transaction.on_commit(queue_task)
