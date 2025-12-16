from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

from instagram.misc import get_post_media_upload_location
from instagram.models.user import User


class Post(models.Model):
    POST_VARIANT_NORMAL = "normal"
    POST_VARIANT_CAROUSEL = "carousel"

    POST_VARIANTS = (
        (POST_VARIANT_NORMAL, "Normal"),
        (POST_VARIANT_CAROUSEL, "Carousel"),
    )

    id = models.CharField(max_length=50, primary_key=True, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    variant = models.CharField(
        max_length=15,
        choices=POST_VARIANTS,
        default=POST_VARIANT_NORMAL,
    )
    thumbnail_url = models.URLField(max_length=2500)
    thumbnail = models.ImageField(
        upload_to=get_post_media_upload_location,
        blank=True,
        null=True,
    )
    blur_data_url = models.TextField(blank=True)
    raw_data = models.JSONField(blank=True, null=True)
    post_created_at = models.DateTimeField(default=timezone.now)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.user.username} - {self.id}"

    def save(self, *args, **kwargs):
        return super().save(*args, **kwargs)

    def generate_blur_data_url_task(self):
        """
        Generates a blurred data URL from the thumbnail_url using a Celery task.
        This method queues the blur data URL generation as a background task.
        """
        from instagram.tasks import post_generate_blur_data_url  # noqa: PLC0415

        post_generate_blur_data_url.delay(self.id)

    def _handle_post_carousel(self):
        """
        Handles the post carousel variant.
        """

        # Update variant to carousel
        self.variant = self.POST_VARIANT_CAROUSEL
        self.save()

        # Create PostMedia objects for each media in the carousel
        carousel_media = self.raw_data.get("carousel_media", [])

        for media in carousel_media:
            obj, _ = PostMedia.objects.get_or_create(
                post=self,
                reference=media.get("strong_id__"),
                defaults={
                    "thumbnail_url": media.get("display_uri"),
                    "media_url": media.get("display_uri"),
                },
            )

    def _get_post_details_from_api(self):
        """
        Fetch post details from Instagram API using the post ID.

        Returns:
            Dictionary containing post details from the API response

        Raises:
            ImproperlyConfigured: If API settings are not configured
            requests.RequestException: If the API request fails
        """
        from core.utils.instagram_api import fetch_post_by_id  # noqa: PLC0415

        response = fetch_post_by_id(self.id)
        data = response.get("data", {})

        if data and not data.get("status"):
            msg = f"Failed to fetch post details for post_id {self.id}: {data.get('errorMessage')}"  # noqa: E501
            raise Exception(msg)  # noqa: TRY002

        return data


class PostMedia(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    reference = models.CharField(max_length=50, default="")

    thumbnail_url = models.URLField(max_length=2500)
    media_url = models.URLField(max_length=2500)

    thumbnail = models.ImageField(
        upload_to=get_post_media_upload_location,
        blank=True,
        null=True,
    )
    media = models.FileField(
        upload_to=get_post_media_upload_location,
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("post", "reference")

    def __str__(self):
        return f"{self.post.user.username} - {self.post.id}"
