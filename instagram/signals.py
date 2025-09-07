import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User
from .tasks import update_profile_picture_from_url

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def user_post_save(sender, instance, created, **kwargs):
    """
    Trigger profile picture update task when User is saved.
    Only triggers if original_profile_picture_url is present.
    """
    # Only trigger if we have an Instagram profile picture URL
    if instance.original_profile_picture_url:
        # Use delay to run task asynchronously
        update_profile_picture_from_url.delay(str(instance.uuid))
        logger.info("Profile picture update task queued for user %s", instance.username)
