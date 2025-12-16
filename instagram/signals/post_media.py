import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from instagram.models import PostMedia
from instagram.tasks.post import download_post_media_from_url
from instagram.tasks.post import download_post_media_thumbnail_from_url
from instagram.tasks.post import post_media_generate_blur_data_url

logger = logging.getLogger(__name__)


@receiver(post_save, sender=PostMedia)
def post_media_post_save(sender, instance, created, **kwargs):
    """
    Trigger download tasks when PostMedia is saved.
    - Thumbnail: if thumbnail_url exists but thumbnail field is empty
    - Media: if media_url exists but media field is empty
    - Blur Data URL: if thumbnail_url exists but blur_data_url is empty
    Uses transaction.on_commit() to ensure tasks run after DB commit.
    """
    # Queue thumbnail download if needed
    if instance.thumbnail_url and not instance.thumbnail:
        # Use transaction.on_commit to ensure the task only runs after
        # the database transaction is committed
        def queue_thumbnail_task():
            download_post_media_thumbnail_from_url.delay(instance.id)
            logger.info(
                "Thumbnail download task queued for post media %s",
                instance.id,
            )

        transaction.on_commit(queue_thumbnail_task)

    # Queue media download if needed
    if instance.media_url and not instance.media:
        # Use transaction.on_commit to ensure the task only runs after
        # the database transaction is committed
        def queue_media_task():
            download_post_media_from_url.delay(instance.id)
            logger.info(
                "Media download task queued for post media %s",
                instance.id,
            )

        transaction.on_commit(queue_media_task)

    # Queue blur data URL generation if needed
    if instance.thumbnail_url and not instance.blur_data_url:
        # Use transaction.on_commit to ensure the task only runs after
        # the database transaction is committed
        def queue_blur_data_url_task():
            post_media_generate_blur_data_url.delay(instance.id)
            logger.info(
                "Blur data URL generation task queued for post media %s",
                instance.id,
            )

        transaction.on_commit(queue_blur_data_url_task)
