from django.urls import path

from payments.views import StripeWebhookView

urlpatterns = [
    path("webhooks/stripe/", StripeWebhookView.as_view(), name="stripe-webhook"),
]


app_name = "payments"
