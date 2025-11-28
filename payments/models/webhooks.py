from django.db import models


class WebhookLog(models.Model):
    REFERENCE_STRIPE = "STRIPE"
    REFERENCE_CHOICES = [
        (REFERENCE_STRIPE, "Stripe"),
    ]

    reference_type = models.CharField(max_length=20, choices=REFERENCE_CHOICES)
    reference = models.CharField(max_length=255)
    remarks = models.TextField(default="")

    raw_data = models.JSONField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Webhook Log {self.reference} - {self.reference_type}"
