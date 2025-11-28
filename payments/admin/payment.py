from django.contrib import admin
from django.contrib import messages
from django.http import HttpRequest
from django.shortcuts import redirect
from django.urls import reverse_lazy
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin
from unfold.decorators import action

from payments.models import Payment


@admin.register(Payment)
class PaymentAdmin(SimpleHistoryAdmin, ModelAdmin):
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
    readonly_fields = (
        "user",
        "reference_type",
        "reference",
        "status",
        "amount",
        "raw_data",
        "url",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "General",
            {
                "fields": (
                    ("user", "status"),
                    ("reference_type", "reference"),
                    "amount",
                    "url",
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

    actions_detail = [
        "update_from_stripe",
    ]

    @action(
        description=("Update from Stripe"),
        url_path="update-from-stripe",
    )
    def update_from_stripe(self, request: HttpRequest, object_id: int):
        payment = Payment.objects.get(pk=object_id)

        try:
            payment.update_status()
            messages.success(request, "Payment status updated successfully.")
            return redirect(
                reverse_lazy("admin:payments_payment_change", args=(object_id,)),
            )
        except Exception as e:  # noqa: BLE001
            messages.error(request, str(e))
            return redirect(
                reverse_lazy("admin:payments_payment_change", args=(object_id,)),
            )
