import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from payments.gateways.factory import PaymentGatewayFactory
from payments.models import Payment
from payments.models import WebhookLog
from payments.tasks import process_checkout_session_completed
from payments.tasks import process_payment_intent_succeeded

logger = logging.getLogger(__name__)


class StripeWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        """
        Handle a webhook request from any payment gateway.
        """

        # Determine gateway type from request
        gateway_type = self._determine_gateway_type(request)

        try:
            # Get the appropriate gateway
            gateway = PaymentGatewayFactory.get_gateway(gateway_type)

            # Validate signature
            payload = request.body
            signature = request.headers.get("stripe-signature")

            if not gateway.validate_webhook_signature(payload, signature):
                msg = "Invalid webhook signature"
                raise ValueError(msg)  # noqa: TRY301

        except ValueError as e:
            # Log the webhook request even if it's invalid
            WebhookLog.objects.create(
                reference_type=gateway_type,
                reference="",
                raw_data=request.data,
                remarks=str(e),
            )
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Process webhook event
        event_info = gateway.process_webhook_event(request.data)

        # Log webhook
        WebhookLog.objects.create(
            reference_type=gateway_type,
            reference=event_info["reference"],
            raw_data=request.data,
            remarks=event_info["event_type"],
        )

        event_type = event_info["event_type"]

        if event_type == "checkout.session.completed":
            # Queue Celery task for async processing
            checkout_session_id = event_info["reference"]
            process_checkout_session_completed.delay(checkout_session_id, request.data)
            logger.info(
                "Queued checkout.session.completed processing for %s",
                checkout_session_id,
            )
        elif event_type == "payment_intent.succeeded":
            # Queue Celery task for async processing
            payment_intent_id = event_info["reference"]
            process_payment_intent_succeeded.delay(payment_intent_id, request.data)
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

    def _determine_gateway_type(self, request):
        """
        Determine gateway type from request.

        For now, assume Stripe. In the future, this can be enhanced by:
        - Checking URL path (e.g., /webhooks/stripe/, /webhooks/paypal/)
        - Checking specific headers unique to each gateway
        - Using different webhook endpoints for different gateways
        """
        return Payment.REFERENCE_STRIPE
