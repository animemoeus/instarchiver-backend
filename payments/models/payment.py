from django.db import models

from core.users.models import User


class Payment(models.Model):
    STATUS_UNPAID = "UNPAID"
    STATUS_PAID = "PAID"
    STATUS_FAILED = "FAILED"
    STATUS_CHOICES = [
        (STATUS_UNPAID, "Unpaid"),
        (STATUS_PAID, "Paid"),
        (STATUS_FAILED, "Failed"),
    ]

    REFERENCE_STRIPE = "STRIPE"
    REFERENCE_CHOICES = [
        (REFERENCE_STRIPE, "Stripe"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reference_type = models.CharField(max_length=20, choices=REFERENCE_CHOICES)
    reference = models.CharField(max_length=100, unique=True)
    url = models.URLField()
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_UNPAID,
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    raw_data = models.JSONField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment {self.reference} - {self.status}"
