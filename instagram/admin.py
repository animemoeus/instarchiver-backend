from django.contrib import admin
from django.contrib import messages
from django.http import HttpRequest
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin
from unfold.decorators import action

from .models import Story
from .models import User
from .models import UserUpdateStoryLog


@admin.register(User)
class InstagramUserAdmin(SimpleHistoryAdmin, ModelAdmin):
    actions_detail = ["update_from_api", "update_stories_from_api"]
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

    @action(
        description=_("Update from Instagram API"),
        url_path="update-from-api",
        permissions=["change"],
    )
    def update_from_api(self, request: HttpRequest, object_id: str):
        """Update user profile data from Instagram API."""
        try:
            user = User.objects.get(pk=object_id)
            user.update_profile_from_api()
            messages.success(
                request,
                f"Successfully updated {user.username} from Instagram API.",
            )
        except Exception as e:  # noqa: BLE001
            messages.error(
                request,
                "Failed to update user from API: %s" % str(e),  # noqa: UP031
            )

        return redirect(reverse("admin:instagram_user_change", args=(object_id,)))

    @action(
        description=_("Update stories from Instagram API"),
        url_path="update-stories-from-api",
        permissions=["change"],
    )
    def update_stories_from_api(self, request: HttpRequest, object_id: str):
        """Update user stories from Instagram API asynchronously."""
        try:
            user = User.objects.get(pk=object_id)
            task_result = user.update_stories_from_api_async()
            messages.success(
                request,
                f"Successfully queued story update task for {user.username}. Task ID: {task_result.id}",  # noqa: E501
            )
        except Exception as e:  # noqa: BLE001
            messages.error(
                request,
                "Failed to queue story update task: %s" % str(e),  # noqa: UP031
            )

        return redirect(reverse("admin:instagram_user_change", args=(object_id,)))


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
        "created_at",
        "updated_at",
    ]
    ordering = ["-created_at"]


@admin.register(Story)
class StoryAdmin(ModelAdmin):
    list_display = [
        "story_id",
        "user",
        "created_at",
        "story_created_at",
    ]
    list_filter = [
        "user",
        "created_at",
        "story_created_at",
    ]
    search_fields = [
        "story_id",
        "user__username",
    ]
    readonly_fields = [
        "story_id",
        "created_at",
    ]
    ordering = ["-created_at"]
