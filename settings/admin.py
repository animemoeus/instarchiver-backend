from django.contrib import admin
from solo.admin import SingletonModelAdmin
from unfold.admin import ModelAdmin

from .models import CoreAPISetting
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


@admin.register(CoreAPISetting)
class CoreAPISettingAdmin(SingletonModelAdmin, ModelAdmin):
    fieldsets = (
        (
            "Core API Configuration",
            {
                "fields": ("api_url", "api_token"),
                "description": "Configure Core API settings",
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
