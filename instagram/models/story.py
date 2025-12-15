from django.db import models

from instagram.misc import get_user_story_upload_location


class Story(models.Model):
    story_id = models.CharField(unique=True, max_length=50, primary_key=True)
    user = models.ForeignKey("instagram.User", on_delete=models.CASCADE)
    thumbnail_url = models.URLField(max_length=2500, blank=True)
    blur_data_url = models.TextField(blank=True)
    media_url = models.URLField(max_length=2500, blank=True)

    thumbnail = models.ImageField(
        upload_to=get_user_story_upload_location,
        blank=True,
        null=True,
    )
    media = models.FileField(
        upload_to=get_user_story_upload_location,
        blank=True,
        null=True,
    )
    raw_api_data = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    story_created_at = models.DateTimeField()

    class Meta:
        verbose_name = "Story"
        verbose_name_plural = "Stories"

    def __str__(self):
        return f"{self.user.username} - {self.story_id}"

    def generate_blur_data_url_task(self):
        """
        Generates a blurred data URL from the media_url using a Celery task.
        This method queues the blur data URL generation as a background task.
        """
        from instagram.tasks import story_generate_blur_data_url  # noqa: PLC0415

        story_generate_blur_data_url.delay(self.story_id)


class UserUpdateStoryLog(models.Model):
    STATUS_PENDING = "PENDING"
    STATUS_IN_PROGRESS = "IN_PROGRESS"
    STATUS_COMPLETED = "COMPLETED"
    STATUS_FAILED = "FAILED"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
    ]

    user = models.ForeignKey("instagram.User", on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Update Story Log"
        verbose_name_plural = "User Update Story Logs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Story Update for {self.user.username} - {self.status}"
