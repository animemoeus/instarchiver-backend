import logging

import stripe
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from payments.models import WebhookLog
from settings.models import StripeSetting

logger = logging.getLogger(__name__)


class StripeWebhookView(APIView):
    authentication_classes = []
    permission_classes = []
    parser_classes = []  # Disable DRF parsing to preserve raw request body

    def post(self, request):
        """
        Handle a Stripe webhook request.
        """

        try:
            event = self.validate_signature(request)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        webhook_log = WebhookLog(
            reference_type=WebhookLog.REFERENCE_STRIPE,
            reference=event.get("id"),
            raw_data=event,
        )
        webhook_log.save()

        return Response({"status": "ok"})

    def validate_signature(self, request):
        """
        Validate the signature of the request and return the parsed event.
        """

        stripe_settings = StripeSetting.get_solo()
        webhook_secret = stripe_settings.webhook_secret

        if not webhook_secret:
            msg = "Missing Stripe webhook secret"
            logger.error(msg)
            raise ValueError(msg)

        # Get the raw body and signature header
        payload = request.body
        sig_header = request.headers.get("stripe-signature")

        # Debug logging
        logger.info(
            f"Webhook secret configured: {webhook_secret[:10]}..."
            if webhook_secret
            else "No secret",
        )

        if not sig_header:
            msg = "Missing Stripe signature header"
            logger.error(msg)
            raise ValueError(msg)

        try:
            # Verify the webhook signature and construct the event
            return stripe.Webhook.construct_event(
                payload=payload,
                sig_header=sig_header,
                secret=webhook_secret,
            )
        except stripe.error.SignatureVerificationError as e:
            msg = f"Stripe signature verification failed: {e}"
            logger.exception(msg)
            raise ValueError(msg) from e
        except ValueError as e:
            msg = f"Invalid webhook payload: {e}"
            logger.exception(msg)
            raise ValueError(msg) from e
