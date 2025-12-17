import base64
import logging

from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

from core.utils.openai import get_openai_client
from instagram.misc import get_post_media_upload_location
from instagram.models.user import User


class Post(models.Model):
    POST_VARIANT_NORMAL = "normal"
    POST_VARIANT_CAROUSEL = "carousel"
    POST_VARIANT_VIDEO = "video"

    POST_VARIANTS = (
        (POST_VARIANT_NORMAL, "Normal"),
        (POST_VARIANT_CAROUSEL, "Carousel"),
        (POST_VARIANT_VIDEO, "Video"),
    )

    id = models.CharField(max_length=50, primary_key=True, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    variant = models.CharField(
        max_length=15,
        choices=POST_VARIANTS,
        default=POST_VARIANT_NORMAL,
    )
    caption = models.TextField(blank=True)
    thumbnail_url = models.URLField(max_length=2500)
    thumbnail = models.ImageField(
        upload_to=get_post_media_upload_location,
        blank=True,
        null=True,
    )
    thumbnail_insight = models.TextField(blank=True)
    thumbnail_insight_token_usage = models.IntegerField(default=0)
    width = models.IntegerField(blank=True, null=True)
    height = models.IntegerField(blank=True, null=True)
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

    def generate_thumbnail_insight_task(self):
        """
        Generates AI-powered thumbnail insight using a Celery task.
        This method queues the thumbnail insight generation as a background task.
        """
        from instagram.tasks import generate_post_thumbnail_insight  # noqa: PLC0415

        generate_post_thumbnail_insight.delay(self.id)

    def generate_thumbnail_insight(self):
        """
        Generate AI-powered insight for the post thumbnail using OpenAI Vision API.

        This method encodes the thumbnail image and sends it to OpenAI's GPT-4 Vision
        model to generate a descriptive insight about the post content.

        Returns:
            str: Generated insight text, or empty string if generation fails

        Raises:
            ValueError: If thumbnail file doesn't exist
            ImproperlyConfigured: If OpenAI settings are not configured
        """
        logger = logging.getLogger(__name__)

        # Check if thumbnail exists
        if not self.thumbnail:
            msg = f"Thumbnail file does not exist for post {self.id}"
            raise ValueError(msg)

        try:
            # Encode image to base64
            # Use .open() instead of .path for S3 compatibility
            with self.thumbnail.open("rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode("utf-8")

            # Get OpenAI client and model
            client = get_openai_client()
            model_name = "gpt-5-mini"

            # Create chat completion with vision
            prompt_text = (
                "Analyze this Instagram post image and provide a brief, "
                "engaging insight about what's shown in the image. "
                "Keep it concise (2-3 sentences)."
            )
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt_text,
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                },
                            },
                        ],
                    },
                ],
            )

            # Extract and save the insight
            insight = response.choices[0].message.content.strip()
            self.thumbnail_insight = insight
            self.thumbnail_insight_token_usage = response.usage.total_tokens
            self.save(
                update_fields=["thumbnail_insight", "thumbnail_insight_token_usage"],
            )

        except FileNotFoundError:
            logger.exception("Thumbnail file not found for post %s", self.id)
            raise
        except Exception:
            logger.exception(
                "Failed to generate thumbnail insight for post %s",
                self.id,
            )
            return ""
        else:
            logger.info("Generated thumbnail insight for post %s", self.id)

    def process_post_by_type(self):
        """
        Determines the post type from raw_data and calls the appropriate handler.
        - Carousel posts: have carousel_media in raw_data
        - Video posts: have video_versions in raw_data
        - Normal posts: single image posts (default)

        This method is idempotent and safe to call multiple times.
        """
        if not self.raw_data:
            return

        # Determine post type and call appropriate handler
        if self.raw_data.get("carousel_media"):
            self.handle_post_carousel()
        elif self.raw_data.get("video_versions"):
            self.handle_post_video()
        else:
            self.handle_post_normal()

    def handle_post_normal(self):
        """
        Handles the post normal variant.
        Idempotent - safe to call multiple times.
        """

        # If carousel_media exists, it's a carousel post
        if self.raw_data and self.raw_data.get("carousel_media"):
            return

        # Use update() to avoid triggering post_save signal
        Post.objects.filter(id=self.id).update(variant=self.POST_VARIANT_NORMAL)
        # Update local instance to reflect change
        self.variant = self.POST_VARIANT_NORMAL

        # Create PostMedia object for the post
        PostMedia.objects.get_or_create(
            post=self,
            reference=self.raw_data.get("id"),
            defaults={
                "thumbnail_url": self.raw_data.get("image_versions2")
                .get("candidates")[0]
                .get("url"),
                "media_url": self.raw_data.get("image_versions2")
                .get("candidates")[0]
                .get("url"),
            },
        )

    def handle_post_carousel(self):
        """
        Handles the post carousel variant.
        Idempotent - safe to call multiple times.
        """

        # Use update() to avoid triggering post_save signal
        Post.objects.filter(id=self.id).update(variant=self.POST_VARIANT_CAROUSEL)
        # Update local instance to reflect change
        self.variant = self.POST_VARIANT_CAROUSEL

        # Create PostMedia objects for each media in the carousel
        carousel_media = self.raw_data.get("carousel_media", [])

        for media in carousel_media:
            _, _ = PostMedia.objects.get_or_create(
                post=self,
                reference=media.get("strong_id__"),
                defaults={
                    "thumbnail_url": media.get("display_uri"),
                    "media_url": media.get("display_uri"),
                },
            )

    def handle_post_video(self):
        """
        Handles the post video variant.
        Idempotent - safe to call multiple times.
        """

        # Use update() to avoid triggering post_save signal
        Post.objects.filter(id=self.id).update(variant=self.POST_VARIANT_VIDEO)
        # Update local instance to reflect change
        self.variant = self.POST_VARIANT_VIDEO

        # If no video_versions, it's not a video post
        if self.raw_data and not self.raw_data.get("video_versions"):
            return

        PostMedia.objects.get_or_create(
            post=self,
            reference=self.raw_data.get("id"),
            defaults={
                "thumbnail_url": self.raw_data.get("image_versions2")
                .get("candidates")[0]
                .get("url"),
                "media_url": self.raw_data.get("video_versions")[0].get("url"),
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
    blur_data_url = models.TextField(blank=True)

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
    width = models.IntegerField(blank=True, null=True)
    height = models.IntegerField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("post", "reference")

    def __str__(self):
        return f"{self.post.user.username} - {self.post.id}"

    def generate_blur_data_url_task(self):
        """
        Generates a blurred data URL from the thumbnail_url using a Celery task.
        This method queues the blur data URL generation as a background task.
        """
        from instagram.tasks import post_media_generate_blur_data_url  # noqa: PLC0415

        post_media_generate_blur_data_url.delay(self.id)
