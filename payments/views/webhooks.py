import logging

import stripe
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from payments.models import WebhookLog
from payments.tasks import process_checkout_session_completed
from payments.tasks import process_payment_intent_succeeded
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
            # Log the webhook request even if it's invalid
            WebhookLog.objects.create(
                reference_type=WebhookLog.REFERENCE_STRIPE,
                reference="",
                raw_data=request.data,
                remarks=str(e),
            )
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
            # Queue Celery task for async processing
            checkout_session_id = data.get("data", {}).get("object", {}).get("id")
            process_checkout_session_completed.delay(checkout_session_id, data)
            logger.info(
                "Queued checkout.session.completed processing for %s",
                checkout_session_id,
            )
        elif event_type == "payment_intent.succeeded":
            # Queue Celery task for async processing
            payment_intent_id = data.get("data", {}).get("object", {}).get("id")
            process_payment_intent_succeeded.delay(payment_intent_id, data)
            logger.info(
                "Queued payment_intent.succeeded processing for %s",
                payment_intent_id,
            )
        else:
            logger.warning(
                "Unknown event type '%s'. Skipping event processing.",
                event_type,
            )

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
