from django.urls import path

from payments.views import PaymentListCreateAPIView
from payments.views import StripeWebhookView

urlpatterns = [
    path("", PaymentListCreateAPIView.as_view(), name="payment-list-create"),
    path("webhooks/stripe/", StripeWebhookView.as_view(), name="stripe-webhook"),
]


app_name = "payments"
