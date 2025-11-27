from django.contrib import admin
from unfold.admin import ModelAdmin

from payments.models import Payment


@admin.register(Payment)
class PaymentAdmin(ModelAdmin):
    list_display = (
        "id",
        "user",
        "reference_type",
        "reference",
        "status",
        "amount",
        "created_at",
    )
    list_filter = ("status", "reference_type", "created_at")
    search_fields = ("reference", "user__username", "user__email")
    readonly_fields = ("created_at", "updated_at", "raw_data", "url")

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "user",
                    "reference_type",
                    "reference",
                    "status",
                    "amount",
                    "url",
                ),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
            },
        ),
        (
            "Raw Data",
            {
                "fields": ("raw_data",),
            },
        ),
    )
