from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin

from .models import User


@admin.register(User)
class InstagramUserAdmin(SimpleHistoryAdmin, ModelAdmin):
    list_display = [
        "username",
        "full_name",
        "instagram_id",
        "is_private",
        "is_verified",
        "follower_count",
        "media_count",
        "created_at",
        "api_updated_at",
    ]
    list_filter = [
        "is_private",
        "is_verified",
        "allow_auto_update_stories",
        "allow_auto_update_profile",
        "created_at",
        "api_updated_at",
    ]
    search_fields = ["username", "full_name", "instagram_id"]
    readonly_fields = [
        "uuid",
        "created_at",
        "updated_at",
        "api_updated_at",
        "raw_api_data",
    ]
    fieldsets = (
        (
            "General",
            {
                "fields": (
                    "username",
                    "instagram_id",
                    "full_name",
                    "biography",
                    "profile_picture",
                    "original_profile_picture_url",
                    "is_private",
                    "is_verified",
                    "media_count",
                    "follower_count",
                    "following_count",
                    "allow_auto_update_stories",
                    "allow_auto_update_profile",
                ),
                "classes": ["tab"],
            },
        ),
        (
            "Metadata",
            {
                "fields": (
                    "uuid",
                    "created_at",
                    "updated_at",
                    "api_updated_at",
                    "raw_api_data",
                ),
                "classes": ["tab"],
            },
        ),
    )
    ordering = ["-created_at"]
