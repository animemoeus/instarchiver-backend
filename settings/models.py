from django.db import models
from solo.models import SingletonModel


class OpenAISetting(SingletonModel):
    api_key = models.CharField(
        max_length=255,
        default="",
        blank=True,
        help_text="OpenAI API Key",
    )
    model_name = models.CharField(
        max_length=100,
        default="",
        blank=True,
        help_text="OpenAI Model Name",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "OpenAI Settings"

    class Meta:
        verbose_name = "OpenAI Setting"


class CoreAPISetting(SingletonModel):
    api_url = models.URLField(
        max_length=255,
        default="",
        blank=True,
        help_text="Core API URL",
    )
    api_token = models.CharField(
        max_length=255,
        default="",
        blank=True,
        help_text="Core API Token",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Core API Settings"

    class Meta:
        verbose_name = "Core API Setting"


class FirebaseAdminSetting(SingletonModel):
    service_account_file = models.FileField(
        upload_to="firebase/",
        blank=True,
        null=True,
        help_text="Firebase Admin SDK Service Account JSON file",
    )
    project_id = models.CharField(
        max_length=255,
        default="",
        blank=True,
        help_text="Firebase Project ID (optional, usually in service account file)",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Firebase Admin Settings"

    class Meta:
        verbose_name = "Firebase Admin Setting"
