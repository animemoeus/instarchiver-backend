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

    def post(self, request):
        try:
            self.validate_signature(request)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        webhook_log = WebhookLog(
            reference_type=WebhookLog.REFERENCE_STRIPE,
            reference=request.data.get("id"),
            raw_data=request.data,
        )
        webhook_log.save()

        return Response({"status": "ok"})

    def validate_signature(self, request):
        """
        Validate the signature of the request.
        """

        stripe_settings = StripeSetting.get_solo()
        webhook_secret = stripe_settings.webhook_secret

        if not webhook_secret:
            msg = "Missing Stripe webhook secret"
            logger.error(msg)
            raise ValueError(msg)

        try:
            stripe.Webhook.construct_event(
                payload=request.body,
                sig_header=request.headers.get("stripe-signature"),
                secret=webhook_secret,
            )
        except ValueError as e:
            msg = "Invalid Stripe signature"
            logger.exception(msg)
            raise ValueError(msg) from e
