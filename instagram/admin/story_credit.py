from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin

from instagram.models import StoryCredit


@admin.register(StoryCredit)
class StoryCreditAdmin(SimpleHistoryAdmin, ModelAdmin):
    list_display = [
        "user",
        "credit",
        "created_at",
        "updated_at",
    ]
    list_filter = [
        "created_at",
        "updated_at",
    ]
    search_fields = ["user__username"]
    readonly_fields = [
        "user",
        "credit",
        "created_at",
        "updated_at",
    ]
    fieldsets = (
        (
            "General",
            {
                "fields": (
                    ("user", "credit"),
                    ("created_at", "updated_at"),
                ),
            },
        ),
    )
    ordering = ["-created_at"]
