from django.db import models
from simple_history.models import HistoricalRecords
from solo.models import SingletonModel

from payments.models import Payment


class PaymentSetting(SingletonModel):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Payment Setting"
        verbose_name_plural = "Payment Settings"


class GatewayOption(models.Model):
    name = models.CharField(
        max_length=100,
        choices=Payment.REFERENCE_CHOICES,
        unique=True,
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Gateway Option"
        verbose_name_plural = "Gateway Options"

    def __str__(self):
        return self.name
