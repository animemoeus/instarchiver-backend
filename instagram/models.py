import logging
import uuid

from django.db import models
from django.utils import timezone

from core.utils.instagram_api import fetch_user_info_by_user_id
from core.utils.instagram_api import fetch_user_info_by_username_v2

from .misc import get_user_profile_picture_upload_location

logger = logging.getLogger(__name__)


class User(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    instagram_id = models.CharField(max_length=50, unique=True, blank=True, null=True)
    username = models.CharField(max_length=150, unique=True)
    full_name = models.CharField(max_length=150, blank=True)
    profile_picture = models.ImageField(
        upload_to=get_user_profile_picture_upload_location,
        blank=True,
        null=True,
    )
    original_profile_picture_url = models.URLField(
        max_length=2500,
        blank=True,
        help_text="The original profile picture URL from Instagram",
    )
    biography = models.TextField(blank=True)
    is_private = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    media_count = models.PositiveIntegerField(default=0)
    follower_count = models.PositiveIntegerField(default=0)
    following_count = models.PositiveIntegerField(default=0)

    allow_auto_update_stories = models.BooleanField(default=False)
    allow_auto_update_profile = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    api_updated_at = models.DateTimeField(
        verbose_name="Updated From API",
        blank=True,
        null=True,
    )

    def __str__(self):
        return self.username

    def update_profile_from_api(self):
        """Update user profile from Instagram API using the instance's instagram_id or username."""  # noqa: E501

        # Use instagram_id if available, otherwise use username
        if self.instagram_id:
            response = fetch_user_info_by_user_id(self.instagram_id)
        else:
            response = fetch_user_info_by_username_v2(self.username)

        # Check for errors in the response and throw an exception
        if response.get("data") and not response["data"].get("status"):
            msg = "Error fetching data for user %s. %s " % (  # noqa: UP031
                self.username,
                response["data"].get("errorMessage", ""),
            )
            logger.error(msg)
            raise Exception(msg)  # noqa: TRY002

        # Update timestamp and save
        self.api_updated_at = timezone.now()
        self.save()
