from django.contrib import admin
from unfold.admin import ModelAdmin

from payments.models import WebhookLog


@admin.register(WebhookLog)
class WebhookLogAdmin(ModelAdmin):
    list_display = (
        "reference",
        "reference_type",
        "created_at",
    )
    list_filter = ("reference_type", "created_at")
    search_fields = ("reference",)
    readonly_fields = (
        "reference_type",
        "reference",
        "created_at",
        "updated_at",
        "raw_data",
    )

    fieldsets = (
        (
            "General",
            {
                "fields": (
                    ("reference_type", "reference"),
                    ("created_at", "updated_at"),
                ),
                "classes": ["tab"],
            },
        ),
        (
            "Metadata",
            {
                "fields": ("raw_data",),
                "classes": ["tab"],
            },
        ),
    )
