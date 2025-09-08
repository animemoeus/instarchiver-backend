from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import APIRequestLog


@admin.register(APIRequestLog)
class APIRequestLogAdmin(ModelAdmin):
    list_display = [
        "method",
        "url",
        "status",
        "response_status_code",
        "duration_ms",
        "created_at",
    ]
    list_filter = ["status", "method", "response_status_code", "created_at"]
    search_fields = ["url", "error_message"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]

    fieldsets = [
        (
            "General",
            {
                "fields": [
                    "method",
                    "url",
                    "status",
                    "duration_ms",
                    "error_message",
                    "created_at",
                    "updated_at",
                ],
                "classes": ["tab"],
            },
        ),
        (
            "Request",
            {
                "fields": ["request_headers", "request_params", "request_body"],
                "classes": ["tab"],
            },
        ),
        (
            "Response",
            {
                "fields": ["response_status_code", "response_headers", "response_body"],
                "classes": ["tab"],
            },
        ),
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
