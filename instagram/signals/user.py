import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from instagram.models import User
from instagram.tasks.user import update_profile_picture_from_url

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def user_post_save(sender, instance, created, **kwargs):
    """
    Trigger profile picture update task when User is saved.
    Only triggers if original_profile_picture_url is present.
    Uses transaction.on_commit() to ensure task runs after DB commit.
    """
    # Only trigger if we have an Instagram profile picture URL
    if instance.original_profile_picture_url:
        # Use transaction.on_commit to ensure the task only runs after
        # the database transaction is committed. This prevents race conditions
        # where the Celery task might execute before the database has the
        # updated original_profile_picture_url value.
        def queue_task():
            update_profile_picture_from_url.delay(str(instance.uuid))
            logger.info(
                "Profile picture update task queued for user %s",
                instance.username,
            )

        transaction.on_commit(queue_task)
