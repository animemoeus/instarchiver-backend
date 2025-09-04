from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import User


@admin.register(User)
class InstagramUserAdmin(ModelAdmin):
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
    readonly_fields = ["uuid", "created_at", "updated_at", "api_updated_at"]
    fieldsets = (
        (None, {"fields": ("username", "instagram_id")}),
        (
            "Profile Information",
            {
                "fields": (
                    "full_name",
                    "biography",
                    "profile_picture",
                    "original_profile_picture_url",
                ),
            },
        ),
        (
            "Status",
            {"fields": ("is_private", "is_verified")},
        ),
        (
            "Statistics",
            {
                "fields": (
                    "media_count",
                    "follower_count",
                    "following_count",
                ),
            },
        ),
        (
            "Settings",
            {
                "fields": (
                    "allow_auto_update_stories",
                    "allow_auto_update_profile",
                ),
            },
        ),
        (
            "Metadata",
            {
                "fields": ("uuid", "created_at", "updated_at", "api_updated_at"),
                "classes": ("collapse",),
            },
        ),
    )
    ordering = ["-created_at"]
