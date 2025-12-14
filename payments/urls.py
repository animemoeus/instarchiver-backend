from django.urls import path

from payments.views import GatewayOptionsListAPIView
from payments.views import PaymentListCreateAPIView
from payments.views import StripeWebhookView

urlpatterns = [
    path("", PaymentListCreateAPIView.as_view(), name="payment-list-create"),
    path("gateways/", GatewayOptionsListAPIView.as_view(), name="gateway-options-list"),
    path("webhooks/stripe/", StripeWebhookView.as_view(), name="stripe-webhook"),
]


app_name = "payments"
