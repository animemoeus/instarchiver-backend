from django.contrib import admin
from django.http import HttpRequest
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from solo.admin import SingletonModelAdmin
from unfold.admin import ModelAdmin
from unfold.decorators import action

from core.utils import openai

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

    actions_detail = ["check_connection"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @action(
        description=_("Check Connection"),
        url_path="check-connection",
    )
    def check_connection(self, request: HttpRequest, object_id: int):
        if openai.check_connection():
            self.message_user(request, _("OpenAI API connection is working."))
        else:
            self.message_user(
                request,
                _("Failed to connect to OpenAI API."),
                level="error",
            )

        return redirect(
            reverse_lazy("admin:settings_openaisetting_change", args=(object_id,)),
        )


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

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
