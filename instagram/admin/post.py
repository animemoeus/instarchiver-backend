from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin
from unfold.admin import TabularInline

from instagram.models import Post
from instagram.models import PostMedia


class PostMediaInline(TabularInline):
    """Inline admin for PostMedia."""

    model = PostMedia
    extra = 0
    fields = [
        "thumbnail_url",
        "media_url",
        "thumbnail",
        "media",
    ]
    readonly_fields = [
        "thumbnail_url",
        "media_url",
    ]


@admin.register(Post)
class PostAdmin(SimpleHistoryAdmin, ModelAdmin):
    """Admin interface for Post model."""

    list_display = [
        "id",
        "user",
        "variant",
        "created_at",
        "updated_at",
    ]
    list_filter = [
        "variant",
        "created_at",
        "updated_at",
    ]
    search_fields = [
        "id",
        "user__username",
        "user__full_name",
    ]
    readonly_fields = [
        "id",
        "user",
        "created_at",
        "updated_at",
        "thumbnail_url",
        "raw_data",
        "blur_data_url",
        "post_created_at",
    ]
    fieldsets = (
        (
            "General",
            {
                "fields": (
                    ("id", "post_created_at"),
                    ("user", "variant"),
                    "thumbnail_url",
                    "thumbnail",
                    "blur_data_url",
                ),
                "classes": ["tab"],
            },
        ),
        (
            "Metadata",
            {
                "fields": (
                    ("created_at", "updated_at"),
                    "raw_data",
                ),
                "classes": ["tab"],
            },
        ),
    )
    inlines = [PostMediaInline]
    ordering = ["-created_at"]
