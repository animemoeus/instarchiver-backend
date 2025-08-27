from django.contrib import admin
from solo.admin import SingletonModelAdmin
from unfold.admin import ModelAdmin

from .models import OpenAISetting


@admin.register(OpenAISetting)
class OpenAISettingAdmin(SingletonModelAdmin, ModelAdmin):
    fieldsets = (
        (
            "OpenAI Configuration",
            {
                "fields": ("api_key", "model_name"),
                "description": "Configure OpenAI API settings",
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
            },
        ),
    )
    readonly_fields = ("created_at", "updated_at")
