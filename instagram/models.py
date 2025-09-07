import logging
import uuid

from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

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
        max_length=512,
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
    raw_api_data = models.JSONField(blank=True, null=True)

    allow_auto_update_stories = models.BooleanField(default=False)
    allow_auto_update_profile = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    api_updated_at = models.DateTimeField(
        verbose_name="Updated From API",
        blank=True,
        null=True,
    )
    history = HistoricalRecords()

    def __str__(self):
        return self.username

    def _extract_api_data_from_username_v2(self, data):
        """Extract API response data from fetch_user_info_by_username_v2."""
        if not data:
            return

        self.instagram_id = data.get("pk") or self.instagram_id
        self.username = data.get("username") or self.username
        self.full_name = data.get("full_name", "")
        self.original_profile_picture_url = data.get("profile_pic_url", "")
        self.biography = data.get("biography", "")
        self.is_private = data.get("is_private", False)
        self.is_verified = data.get("is_verified", False)
        self.media_count = data.get("media_count", 0)
        self.follower_count = data.get("follower_count", 0)
        self.following_count = data.get("following_count", 0)

    def _extract_api_data_from_user_id(self, data):
        """Extract API response data from fetch_user_info_by_user_id."""
        if not data:
            return

        self.instagram_id = data.get("id") or self.instagram_id
        self.username = data.get("username") or self.username
        self.full_name = data.get("full_name", "")
        self.original_profile_picture_url = data.get("profile_pic_url", "")
        self.biography = data.get("biography", "")
        self.is_private = data.get("is_private", False)
        self.is_verified = data.get("is_verified", False)

        # For user_id API, media count is nested in edge_owner_to_timeline_media
        media_edge = data.get("edge_owner_to_timeline_media", {})
        self.media_count = media_edge.get("count", 0)

        # Follower and following counts are nested in edge structures
        follower_edge = data.get("edge_followed_by", {})
        self.follower_count = follower_edge.get("count", 0)

        following_edge = data.get("edge_follow", {})
        self.following_count = following_edge.get("count", 0)

    def update_profile_from_api(self):
        """Update user profile from Instagram API using the instance's username first, then instagram_id as fallback."""  # noqa: E501

        # Always try username first
        response = fetch_user_info_by_username_v2(self.username)
        api_method = "username_v2"

        # If username API fails and we have instagram_id, try user_id as fallback
        username_failed = not response.get("data") or not response["data"].get("status")
        if username_failed and self.instagram_id:
            response = fetch_user_info_by_user_id(self.instagram_id)
            api_method = "user_id"

        # Check for errors in the response and throw an exception
        if response.get("data") and not response["data"].get("status"):
            msg = "Error fetching data for user %s. %s " % (  # noqa: UP031
                self.username,
                response["data"].get("errorMessage", ""),
            )
            logger.error(msg)
            raise Exception(msg)  # noqa: TRY002

        data = response.get("data")
        self.raw_api_data = data

        # Use appropriate extraction method based on which API was called
        if api_method == "user_id":
            self._extract_api_data_from_user_id(data)
        else:
            self._extract_api_data_from_username_v2(data)

        # Update timestamp and save
        self.api_updated_at = timezone.now()
        self.save()
