from django.db import models
from simple_history.models import HistoricalRecords

from instagram.misc import get_post_media_upload_location
from instagram.models.user import User


class Post(models.Model):
    POST_VARIANT_NORMAL = "normal"
    POST_VARIANT_CAUROSEL = "carousel"

    POST_VARIANTS = (
        (POST_VARIANT_NORMAL, "Normal"),
        (POST_VARIANT_CAUROSEL, "Carousel"),
    )

    id = models.CharField(max_length=50, primary_key=True, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    variant = models.CharField(max_length=15, choices=POST_VARIANTS)
    thumbnail_url = models.URLField(max_length=2500)
    thumbnail = models.ImageField(
        upload_to=get_post_media_upload_location,
        blank=True,
        null=True,
    )
    blur_data_url = models.TextField(blank=True)
    raw_data = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.user.username} - {self.id}"

    def generate_blur_data_url_task(self):
        """
        Generates a blurred data URL from the thumbnail_url using a Celery task.
        This method queues the blur data URL generation as a background task.
        """
        from instagram.tasks import post_generate_blur_data_url  # noqa: PLC0415

        post_generate_blur_data_url.delay(self.id)


class PostMedia(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)

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

    def __str__(self):
        return f"{self.post.user.username} - {self.post.id}"
