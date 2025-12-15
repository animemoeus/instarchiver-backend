import logging
import uuid

from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

from core.utils.instagram_api import fetch_user_info_by_user_id
from core.utils.instagram_api import fetch_user_info_by_username_v2
from core.utils.instagram_api import fetch_user_posts_by_username
from core.utils.instagram_api import fetch_user_stories_by_username
from instagram.misc import get_user_profile_picture_upload_location

logger = logging.getLogger(__name__)


class GetUserPostMixIn:
    """Mixin class to add post-related functionality to User model."""

    def get_post_data_from_api(self):
        if not self.instagram_id:
            msg = f"User {self.username} has no Instagram ID"
            raise ValueError(msg)

        response = fetch_user_posts_by_username(self.instagram_id)
        return response.get("data").get("items", [])

    def update_post_data_from_api(self):
        from instagram.models import Post  # noqa: PLC0415

        posts = self.get_post_data_from_api()
        for post in posts:
            obj, _ = Post.objects.update_or_create(
                id=post.get("pk"),
                user=self,
            )
            obj.raw_data = post
            obj.thumbnail_url = post.get("display_uri")
            obj.save()

    def update_posts_from_api_async(self):
        """
        Trigger asynchronous update of user posts from Instagram API.
        Use this method to queue the post update as a background task.
        """
        from instagram.tasks import update_user_posts_from_api  # noqa: PLC0415

        logger.info("Queuing post update task for user %s", self.username)
        return update_user_posts_from_api.delay(self.uuid)


class User(models.Model, GetUserPostMixIn):
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

    def delete(self, *args, **kwargs):
        """Delete the user instance and clean up all historical records."""
        # Delete all historical records for this user
        self.history.all().delete()

        # Call the parent delete method
        return super().delete(*args, **kwargs)

    def _extract_api_data_from_username_v2(self, data):
        """Extract API response data from fetch_user_info_by_username_v2.

        The v1 API returns data in a nested structure with edge-based counts.
        """
        if not data:
            return

        # v1 API uses 'id' for the Instagram ID
        instagram_id = data.get("id")
        self.instagram_id = str(instagram_id) or self.instagram_id
        self.username = data.get("username") or self.username
        self.full_name = data.get("full_name", "")
        # v1 API uses 'profile_pic_url_hd' as primary, fallback to 'profile_pic_url'
        self.original_profile_picture_url = (
            data.get("profile_pic_url_hd") or data.get("profile_pic_url") or ""
        )
        self.biography = data.get("biography", "")
        self.is_private = data.get("is_private", False)
        self.is_verified = data.get("is_verified", False)

        # v1 API uses edge structures for counts
        media_edge = data.get("edge_owner_to_timeline_media", {})
        self.media_count = media_edge.get("count", 0)

        follower_edge = data.get("edge_followed_by", {})
        self.follower_count = follower_edge.get("count", 0)

        following_edge = data.get("edge_follow", {})
        self.following_count = following_edge.get("count", 0)

    def _extract_api_data_from_user_id(self, data):
        """Extract API response data from fetch_user_info_by_user_id.

        The v1 API returns data in a nested structure with edge-based counts,
        same format as the username v2 API.
        """
        if not data:
            return

        # v1 API uses 'id' for the Instagram ID
        instagram_id = data.get("id")
        self.instagram_id = str(instagram_id) or self.instagram_id
        self.username = data.get("username") or self.username
        self.full_name = data.get("full_name", "")
        # v1 API uses 'profile_pic_url_hd' as primary, fallback to 'profile_pic_url'
        self.original_profile_picture_url = (
            data.get("profile_pic_url_hd") or data.get("profile_pic_url") or ""
        )
        self.biography = data.get("biography", "")
        self.is_private = data.get("is_private", False)
        self.is_verified = data.get("is_verified", False)

        # v1 API uses edge structures for counts
        media_edge = data.get("edge_owner_to_timeline_media", {})
        self.media_count = media_edge.get("count", 0)

        follower_edge = data.get("edge_followed_by", {})
        self.follower_count = follower_edge.get("count", 0)

        following_edge = data.get("edge_follow", {})
        self.following_count = following_edge.get("count", 0)

    def update_profile_from_api(self):
        """Update user profile from Instagram API using the instance's username first, then instagram_id as fallback."""  # noqa: E501

        # Always try username first
        response = fetch_user_info_by_username_v2(self.username)
        api_method = "username_v2"

        # v2 API uses 'code' field for status (200 = success)
        username_failed = response.get("data") and not response.get("data").get(
            "status",
        )
        if username_failed and self.instagram_id:
            response = fetch_user_info_by_user_id(self.instagram_id)
            api_method = "user_id"

        # Check for errors in the response
        if api_method == "username_v2":
            # v1 API uses 'code' field for status
            if response.get("data") and not response.get("data").get("status"):
                msg = "Error fetching data for user %s. %s" % (  # noqa: UP031
                    self.username,
                    response.get("data").get("errorMessage", "Unknown error"),
                )
                logger.error(msg)
                raise Exception(msg)  # noqa: TRY002
            # v1 API nests user data in response['data']['data']['user']
            data = response.get("data", {}).get("data", {}).get("user")
        else:
            # user_id API now uses v1 structure (same as username_v2)
            if response.get("data") and not response.get("data").get("status"):
                msg = "Error fetching data for user %s. %s" % (  # noqa: UP031
                    self.username,
                    response.get("data").get("errorMessage", "Unknown error"),
                )
                logger.error(msg)
                raise Exception(msg)  # noqa: TRY002
            # v1 API nests user data in response['data']
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

    def _update_stories_from_api(self):
        """Update user stories from Instagram API with full error handling and logging."""  # noqa: E501
        # Import here to avoid circular imports
        from .story import Story  # noqa: PLC0415
        from .story import UserUpdateStoryLog  # noqa: PLC0415

        # Create log entry to track this operation
        log_entry = UserUpdateStoryLog.objects.create(
            user=self,
            status=UserUpdateStoryLog.STATUS_IN_PROGRESS,
            message="Started story update from API",
        )

        try:
            # Fetch stories from Instagram API
            response = fetch_user_stories_by_username(self.username)

            # Check for errors in the response (v2 API uses 'code' field)
            if response.get("code") != 200:  # noqa: PLR2004
                error_message = response.get(
                    "message",
                    "Unknown API error",
                )
                msg = (
                    f"Error fetching stories for user {self.username}. {error_message}"
                )
                logger.error(msg)

                # Update log entry with failure
                log_entry.status = UserUpdateStoryLog.STATUS_FAILED
                log_entry.message = msg
                log_entry.save()

                raise Exception(msg)  # noqa: TRY002, TRY301

            # Extract stories data from v2 API response
            stories_data = response.get("data", {}).get("data", {}).get("items", [])
            updated_stories = []

            # Process each story
            for story_data in stories_data:
                story_id = story_data.get("id")

                # Create or update story with v2 API field names
                story, _ = Story.objects.get_or_create(
                    story_id=story_id,
                    defaults={
                        "story_id": story_id,
                        "user": self,
                        "thumbnail_url": story_data.get("thumbnail_url"),
                        "media_url": story_data.get("video_url")
                        or story_data.get("thumbnail_url"),
                        "story_created_at": story_data.get("taken_at_date"),
                        "raw_api_data": story_data,
                    },
                )

                updated_stories.append(story)

            # Update log entry with success
            log_entry.status = UserUpdateStoryLog.STATUS_COMPLETED
            log_entry.message = f"Successfully updated {len(updated_stories)} stories"
            log_entry.save()

            logger.info(
                "Successfully updated %d stories for user %s",
                len(updated_stories),
                self.username,
            )
            return updated_stories  # noqa: TRY300

        except Exception as e:
            # Update log entry with failure if not
            #  already updated
            if log_entry.status == UserUpdateStoryLog.STATUS_IN_PROGRESS:
                log_entry.status = UserUpdateStoryLog.STATUS_FAILED
                log_entry.message = str(e)
                log_entry.save()

            logger.exception(
                "Failed to update stories for user %s: %s",
                self.username,
                e,  # noqa: TRY401
            )
            raise

    def update_stories_from_api(self):
        """Update user stories from Instagram API synchronously."""
        return self._update_stories_from_api()

    def update_stories_from_api_async(self):
        """
        Trigger asynchronous update of user stories from Instagram API.
        Use this method to queue the story update as a background task.
        """
        from instagram.tasks import update_user_stories_from_api  # noqa: PLC0415

        logger.info("Queuing story update task for user %s", self.username)
        return update_user_stories_from_api.delay(self.uuid)
