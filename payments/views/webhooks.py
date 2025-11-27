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

        event_type = data.get("type")

        if event_type == "checkout.session.completed":
            self.handle_checkout_session_completed(data)
        elif event_type == "payment_intent.succeeded":
            self.handle_payment_intent_succeeded(data)

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
        Maps Stripe payment statuses to Payment model statuses:
        - 'paid' -> STATUS_PAID
        - 'unpaid' -> STATUS_UNPAID
        - 'no_payment_required' -> STATUS_PAID

        Note: Payments that are already PAID will not be updated to prevent downgrades.
        """

        data = data.get("data").get("object")
        payment_id = data.get("id")
        payment_status = data.get("payment_status")

        logger.info(
            "Processing checkout.session.completed for payment %s with status: %s",
            payment_id,
            payment_status,
        )

        if payment_status not in Payment.STATUS_CHOICES:
            logger.warning(
                "Unknown payment status '%s' for payment %s. Skipping status update.",
                payment_status,
                payment_id,
            )
            return

        try:
            # Exclude already PAID payments to prevent downgrade
            payment = (
                Payment.objects.select_for_update()
                .exclude(status=Payment.STATUS_PAID)
                .get(
                    reference_type=Payment.REFERENCE_STRIPE,
                    reference=payment_id,
                )
            )
            payment.status = payment_status
            payment.save()
            logger.info(
                "Updated payment %s status to %s",
                payment_id,
                payment_status,
            )
        except Payment.DoesNotExist:
            logger.warning(
                "Payment with reference %s not found or already paid. "
                "Skipping status update to %s.",
                payment_id,
                payment_status,
            )

    @transaction.atomic
    def handle_payment_intent_succeeded(self, data):
        """
        Handle a payment_intent.succeeded event.
        This event fires when a PaymentIntent has successfully completed payment.

        Note: Our Payment model stores checkout session IDs, not payment intent IDs.
        We need to retrieve the checkout session from the payment intent to find
        the related Payment record.
        """

        data = data.get("data").get("object")
        payment_intent_id = data.get("id")
        payment_status = data.get("status")

        logger.info(
            "Processing payment_intent.succeeded for payment_intent %s with status: %s",
            payment_intent_id,
            payment_status,
        )

        # For payment_intent.succeeded, the status should always be 'succeeded'
        if payment_status != "succeeded":
            logger.warning(
                "Unexpected status '%s' for payment_intent.succeeded event. "
                "Expected 'succeeded'. Skipping update.",
                payment_status,
            )
            return

        # Retrieve the payment intent from Stripe to get the checkout session
        try:
            stripe_settings = StripeSetting.get_solo()
            stripe.api_key = stripe_settings.api_key

            # Get the checkout session ID from the payment intent
            checkout_sessions = stripe.checkout.Session.list(
                payment_intent=payment_intent_id,
                limit=1,
            )

            if not checkout_sessions.data:
                logger.warning(
                    "No checkout session found for payment_intent %s. "
                    "Cannot update payment status.",
                    payment_intent_id,
                )
                return

            checkout_session_id = checkout_sessions.data[0].id

            logger.info(
                "Found checkout session %s for payment_intent %s",
                checkout_session_id,
                payment_intent_id,
            )
        except Exception:
            logger.exception(
                "Error retrieving checkout session for payment_intent %s",
                payment_intent_id,
            )
            return

        # Now update the payment using the checkout session ID
        try:
            # Exclude already PAID payments to prevent downgrade
            payment = (
                Payment.objects.select_for_update()
                .exclude(status=Payment.STATUS_PAID)
                .get(
                    reference_type=Payment.REFERENCE_STRIPE,
                    reference=checkout_session_id,
                )
            )
            payment.status = Payment.STATUS_PAID
            payment.save()
            logger.info(
                "Updated payment %s (checkout_session: %s, payment_intent: %s) "
                "status to %s via payment_intent.succeeded",
                payment.id,
                checkout_session_id,
                payment_intent_id,
                Payment.STATUS_PAID,
            )
        except Payment.DoesNotExist:
            logger.warning(
                "Payment with checkout session reference %s not found or already paid. "
                "Skipping status update. (payment_intent: %s)",
                checkout_session_id,
                payment_intent_id,
            )
