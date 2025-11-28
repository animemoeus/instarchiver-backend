import stripe
from django.db import models
from django.db import transaction
from simple_history.models import HistoricalRecords

from core.users.models import User
from settings.models import StripeSetting


class Payment(models.Model):
    # Stripe Checkout Session payment_status values (official)
    STATUS_PAID = "paid"
    STATUS_UNPAID = "unpaid"
    STATUS_NO_PAYMENT_REQUIRED = "no_payment_required"

    # Custom statuses for additional states
    STATUS_FAILED = "failed"
    STATUS_CANCELED = "canceled"
    STATUS_PROCESSING = "processing"

    STATUS_CHOICES = [
        (STATUS_PAID, "Paid"),
        (STATUS_UNPAID, "Unpaid"),
        (STATUS_NO_PAYMENT_REQUIRED, "No Payment Required"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_FAILED, "Failed"),
        (STATUS_CANCELED, "Canceled"),
    ]

    REFERENCE_STRIPE = "STRIPE"
    REFERENCE_CHOICES = [
        (REFERENCE_STRIPE, "Stripe"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reference_type = models.CharField(max_length=20, choices=REFERENCE_CHOICES)
    reference = models.CharField(max_length=100, unique=True)
    url = models.URLField(max_length=1000)
    status = models.CharField(
        max_length=100,
        choices=STATUS_CHOICES,
        default=STATUS_UNPAID,
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    raw_data = models.JSONField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"Payment {self.reference} - {self.status}"

    @transaction.atomic
    def update_status(self):
        """
        Update payment status from Stripe with row-level locking
        """

        # Acquire a row-level lock on this payment instance
        payment = Payment.objects.select_for_update().get(pk=self.pk)

        # Check if the payment is already paid and raise an error if it is
        if payment.status == Payment.STATUS_PAID:
            msg = "Payment is already paid"
            raise ValueError(msg)

        stripe_setting = StripeSetting.get_solo()
        stripe_secret_key = stripe_setting.api_key

        if not stripe_secret_key:
            msg = "Stripe secret key is not set"
            raise ValueError(msg)

        stripe.api_key = stripe_secret_key
        session = stripe.checkout.Session.retrieve(
            payment.reference,
        )

        payment.status = session.payment_status
        payment.raw_data = session.to_dict()
        payment.save()
