from django.contrib import admin
from unfold.admin import ModelAdmin

from instagram.models import StoryCreditPayment


@admin.register(StoryCreditPayment)
class StoryCreditPaymentAdmin(ModelAdmin):
    list_display = [
        "story_credit",
        "payment",
        "credit",
        "created_at",
        "updated_at",
    ]
    list_filter = [
        "created_at",
        "updated_at",
    ]
    search_fields = [
        "story_credit__user__username",
        "payment__reference",
    ]
    readonly_fields = [
        "story_credit",
        "payment",
        "credit",
        "created_at",
        "updated_at",
    ]
    fieldsets = (
        (
            "General",
            {
                "fields": (
                    ("story_credit", "payment"),
                    "credit",
                    ("created_at", "updated_at"),
                ),
            },
        ),
    )
    ordering = ["-created_at"]
