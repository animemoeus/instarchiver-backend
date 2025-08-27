from django.db import models
from solo.models import SingletonModel


class OpenAISetting(SingletonModel):
    api_key = models.CharField(
        max_length=255,
        default="",
        help_text="OpenAI API Key",
    )
    model_name = models.CharField(
        max_length=100,
        default="",
        help_text="OpenAI Model Name",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "OpenAI Settings"

    class Meta:
        verbose_name = "OpenAI Setting"
