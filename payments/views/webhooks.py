import logging

import stripe
from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from payments.models import Payment
from payments.models import WebhookLog
from settings.models import StripeSetting

logger = logging.getLogger(__name__)


class StripeWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        """
        Handle a Stripe webhook request.
        """

        try:
            self.validate_signature(request)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        data = request.data
        creation_data = {
            "reference_type": WebhookLog.REFERENCE_STRIPE,
            "reference": data.get("id"),
            "raw_data": data,
            "remarks": data.get("type"),
        }

        WebhookLog.objects.create(**creation_data)

        if data.get("type") == "checkout.session.completed":
            self.handle_checkout_session_completed(data)

        return Response({"status": "ok"})

    def validate_signature(self, request):
        """
        Validate the signature of the request and return the parsed event.
        """

        # Get the webhook secret from the settings
        stripe_settings = StripeSetting.get_solo()
        webhook_secret = stripe_settings.webhook_secret

        # Check if the webhook secret is configured
        if not webhook_secret:
            msg = "Missing Stripe webhook secret"
            logger.error(msg)
            raise ValueError(msg)

        # Get the raw body and signature header
        payload = request.body
        sig_header = request.headers.get("stripe-signature")

        if not sig_header:
            msg = "Missing Stripe signature header"
            logger.error(msg)
            raise ValueError(msg)

        try:
            stripe.Webhook.construct_event(
                payload=payload,
                sig_header=sig_header,
                secret=webhook_secret,
            )
        except Exception as e:
            msg = f"Invalid webhook payload: {e}"
            logger.exception(msg)
            raise ValueError(msg) from e

    @transaction.atomic
    def handle_checkout_session_completed(self, data):
        """
        Handle a checkout.session.completed event.
        """

        data = data.get("data").get("object")
        payment_id = data.get("id")
        payment_status = data.get("payment_status")

        if payment_status == "paid":
            payment = Payment.objects.get(
                reference_type=Payment.REFERENCE_STRIPE,
                reference=payment_id,
            )
            payment.status = Payment.STATUS_PAID
            payment.save()
