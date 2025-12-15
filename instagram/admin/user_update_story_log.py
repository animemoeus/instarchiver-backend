from django.contrib import admin
from unfold.admin import ModelAdmin

from instagram.models import UserUpdateStoryLog


@admin.register(UserUpdateStoryLog)
class UserUpdateStoryLogAdmin(ModelAdmin):
    list_display = [
        "user",
        "status",
        "message",
        "created_at",
        "updated_at",
    ]
    list_filter = [
        "status",
        "created_at",
        "updated_at",
    ]
    search_fields = ["user__username"]
    readonly_fields = [
        "user",
        "status",
        "message",
        "created_at",
        "updated_at",
    ]
    ordering = ["-created_at"]
