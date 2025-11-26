"""Stripe payment gateway implementation."""

import logging
from datetime import UTC
from datetime import datetime
from decimal import Decimal

import stripe

from payments.utils.base import BasePaymentGateway
from payments.utils.exceptions import CustomerCreationError
from payments.utils.exceptions import PaymentConfigurationError
from payments.utils.exceptions import PaymentCreationError
from payments.utils.exceptions import PaymentGatewayError
from payments.utils.exceptions import PaymentRetrievalError
from payments.utils.exceptions import RefundError
from payments.utils.exceptions import WebhookProcessingError
from payments.utils.exceptions import WebhookVerificationError
from payments.utils.types import CustomerData
from payments.utils.types import PaymentIntentData
from payments.utils.types import PaymentResult
from payments.utils.types import PaymentStatus
from payments.utils.types import RefundData
from payments.utils.types import RefundResult
from payments.utils.types import WebhookEvent
from settings.models import StripeSetting

logger = logging.getLogger(__name__)


class StripePaymentGateway(BasePaymentGateway):
    """Stripe payment gateway implementation."""

    def __init__(self) -> None:
        """Initialize Stripe payment gateway."""
        super().__init__()
        self._configure_stripe()

    @property
    def gateway_name(self) -> str:
        """Return the gateway name."""
        return "stripe"

    def _raise_missing_api_key(self) -> None:
        """Raise error for missing API key."""
        msg = "Stripe API key is not configured"
        raise PaymentConfigurationError(msg, gateway=self.gateway_name)

    def _validate_configuration(self) -> None:
        """Validate Stripe configuration."""
        try:
            settings = StripeSetting.get_solo()
            if not settings.api_key:
                self._raise_missing_api_key()
        except PaymentConfigurationError:
            raise
        except Exception as e:
            msg = f"Failed to load Stripe configuration: {e}"
            raise PaymentConfigurationError(msg, gateway=self.gateway_name) from e

    def _configure_stripe(self) -> None:
        """Configure Stripe with API key."""
        settings = StripeSetting.get_solo()
        stripe.api_key = settings.api_key

    def _get_webhook_secret(self) -> str:
        """Get webhook secret from settings."""
        settings = StripeSetting.get_solo()
        if not settings.webhook_secret:
            msg = "Stripe webhook secret is not configured"
            raise PaymentConfigurationError(msg, gateway=self.gateway_name)
        return settings.webhook_secret

    def _get_stripe_error_message(self, error: stripe.StripeError) -> str:
        """Extract user-friendly message from Stripe error."""
        return error.user_message if hasattr(error, "user_message") else str(error)

    def _map_stripe_status_to_payment_status(self, stripe_status: str) -> PaymentStatus:
        """Map Stripe payment intent status to standardized PaymentStatus."""
        status_mapping = {
            "requires_payment_method": PaymentStatus.PENDING,
            "requires_confirmation": PaymentStatus.PENDING,
            "requires_action": PaymentStatus.PENDING,
            "processing": PaymentStatus.PROCESSING,
            "requires_capture": PaymentStatus.PROCESSING,
            "succeeded": PaymentStatus.SUCCEEDED,
            "canceled": PaymentStatus.CANCELED,
        }
        return status_mapping.get(stripe_status, PaymentStatus.FAILED)

    def _convert_stripe_payment_to_result(
        self,
        payment_intent: stripe.PaymentIntent,
    ) -> PaymentResult:
        """Convert Stripe PaymentIntent to standardized PaymentResult."""
        return PaymentResult(
            id=payment_intent.id,
            status=self._map_stripe_status_to_payment_status(payment_intent.status),
            amount=Decimal(payment_intent.amount) / 100,  # Convert cents to dollars
            currency=payment_intent.currency,
            customer_id=payment_intent.customer
            if isinstance(payment_intent.customer, str)
            else None,
            payment_method=payment_intent.payment_method
            if isinstance(payment_intent.payment_method, str)
            else None,
            created_at=datetime.fromtimestamp(
                payment_intent.created,
                tz=UTC,
            ).isoformat(),
            metadata=dict(payment_intent.metadata) if payment_intent.metadata else {},
            gateway_response=payment_intent.to_dict(),
        )

    def create_payment_intent(self, payment_data: PaymentIntentData) -> PaymentResult:
        """Create a Stripe payment intent."""
        try:
            # Convert amount to cents (Stripe requires integer cents)
            amount_cents = int(payment_data["amount"] * 100)

            # Build payment intent params
            intent_params: dict = {
                "amount": amount_cents,
                "currency": payment_data["currency"],
            }

            # Add optional customer
            if payment_data.get("customer_id"):
                intent_params["customer"] = payment_data["customer_id"]

            # Add payment method types
            if payment_data.get("payment_method_types"):
                intent_params["payment_method_types"] = payment_data[
                    "payment_method_types"
                ]
            else:
                intent_params["automatic_payment_methods"] = {"enabled": True}

            # Add description
            if payment_data.get("description"):
                intent_params["description"] = payment_data["description"]

            # Add metadata
            if payment_data.get("metadata"):
                intent_params["metadata"] = payment_data["metadata"]

            # Add return URL for redirect-based payment methods
            if payment_data.get("return_url"):
                intent_params["return_url"] = payment_data["return_url"]

            # Create payment intent
            payment_intent = stripe.PaymentIntent.create(**intent_params)

            logger.info(
                "Stripe payment intent created successfully: %s",
                payment_intent.id,
            )
            return self._convert_stripe_payment_to_result(payment_intent)

        except stripe.StripeError as e:
            logger.exception("Stripe payment creation failed")
            msg = f"Failed to create payment: {self._get_stripe_error_message(e)}"
            raise PaymentCreationError(
                msg,
                gateway=self.gateway_name,
                original_error=e,
            ) from e
        except Exception as e:
            logger.exception("Unexpected error during payment creation")
            msg = f"Unexpected error creating payment: {e}"
            raise PaymentCreationError(
                msg,
                gateway=self.gateway_name,
                original_error=e,
            ) from e

    def retrieve_payment(self, payment_id: str) -> PaymentResult:
        """Retrieve a Stripe payment intent."""
        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment_id)
            logger.info("Stripe payment intent retrieved successfully: %s", payment_id)
            return self._convert_stripe_payment_to_result(payment_intent)

        except stripe.StripeError as e:
            logger.exception("Stripe payment retrieval failed")
            msg = f"Failed to retrieve payment: {self._get_stripe_error_message(e)}"
            raise PaymentRetrievalError(
                msg,
                gateway=self.gateway_name,
                original_error=e,
            ) from e
        except Exception as e:
            logger.exception("Unexpected error during payment retrieval")
            msg = f"Unexpected error retrieving payment: {e}"
            raise PaymentRetrievalError(
                msg,
                gateway=self.gateway_name,
                original_error=e,
            ) from e

    def create_refund(self, refund_data: RefundData) -> RefundResult:
        """Create a Stripe refund."""
        try:
            refund_params: dict = {
                "payment_intent": refund_data["payment_id"],
            }

            # Add amount if partial refund
            if refund_data.get("amount"):
                amount_cents = int(refund_data["amount"] * 100)
                refund_params["amount"] = amount_cents

            # Add reason
            if refund_data.get("reason"):
                refund_params["reason"] = refund_data["reason"]

            # Add metadata
            if refund_data.get("metadata"):
                refund_params["metadata"] = refund_data["metadata"]

            refund = stripe.Refund.create(**refund_params)

            logger.info("Stripe refund created successfully: %s", refund.id)

            return RefundResult(
                id=refund.id,
                payment_id=refund.payment_intent
                if isinstance(refund.payment_intent, str)
                else "",
                amount=Decimal(refund.amount) / 100,
                currency=refund.currency,
                status=refund.status,
                created_at=datetime.fromtimestamp(refund.created, tz=UTC).isoformat(),
                reason=refund.reason,
                gateway_response=refund.to_dict(),
            )

        except stripe.StripeError as e:
            logger.exception("Stripe refund creation failed")
            msg = f"Failed to create refund: {self._get_stripe_error_message(e)}"
            raise RefundError(msg, gateway=self.gateway_name, original_error=e) from e
        except Exception as e:
            logger.exception("Unexpected error during refund creation")
            msg = f"Unexpected error creating refund: {e}"
            raise RefundError(msg, gateway=self.gateway_name, original_error=e) from e

    def create_customer(self, customer_data: CustomerData) -> dict[str, str]:
        """Create a Stripe customer."""
        try:
            customer_params: dict = {}

            if customer_data.get("email"):
                customer_params["email"] = customer_data["email"]
            if customer_data.get("name"):
                customer_params["name"] = customer_data["name"]
            if customer_data.get("phone"):
                customer_params["phone"] = customer_data["phone"]
            if customer_data.get("address"):
                customer_params["address"] = customer_data["address"]
            if customer_data.get("metadata"):
                customer_params["metadata"] = customer_data["metadata"]

            customer = stripe.Customer.create(**customer_params)

            logger.info("Stripe customer created successfully: %s", customer.id)

            return {
                "id": customer.id,
                "email": customer.email or "",
                "name": customer.name or "",
                "created_at": datetime.fromtimestamp(
                    customer.created,
                    tz=UTC,
                ).isoformat(),
            }

        except stripe.StripeError as e:
            logger.exception("Stripe customer creation failed")
            msg = f"Failed to create customer: {self._get_stripe_error_message(e)}"
            raise CustomerCreationError(
                msg,
                gateway=self.gateway_name,
                original_error=e,
            ) from e
        except Exception as e:
            logger.exception("Unexpected error during customer creation")
            msg = f"Unexpected error creating customer: {e}"
            raise CustomerCreationError(
                msg,
                gateway=self.gateway_name,
                original_error=e,
            ) from e

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        secret: str | None = None,
    ) -> bool:
        """Verify Stripe webhook signature."""
        try:
            webhook_secret = secret or self._get_webhook_secret()
            stripe.Webhook.construct_event(payload, signature, webhook_secret)
        except ValueError as e:
            logger.warning("Invalid Stripe webhook payload: %s", e)
            return False
        except stripe.SignatureVerificationError as e:
            logger.warning("Invalid Stripe webhook signature: %s", e)
            return False
        except Exception as e:
            logger.exception("Unexpected error verifying Stripe webhook")
            msg = f"Failed to verify webhook signature: {e}"
            raise WebhookVerificationError(
                msg,
                gateway=self.gateway_name,
                original_error=e,
            ) from e
        else:
            return True

    def process_webhook(self, payload: dict) -> WebhookEvent:
        """Process Stripe webhook payload."""
        try:
            event_type = payload.get("type", "")
            data_object = payload.get("data", {}).get("object", {})

            # Extract payment ID if available
            payment_id = None
            if "payment_intent" in data_object:
                payment_id = data_object["payment_intent"]
            elif "id" in data_object and data_object.get("object") == "payment_intent":
                payment_id = data_object["id"]

            logger.info(
                "Processing Stripe webhook event: %s (payment_id: %s)",
                event_type,
                payment_id,
            )

            return WebhookEvent(
                event_type=event_type,
                payment_id=payment_id,
                data=data_object,
                gateway_response=payload,
            )

        except Exception as e:
            logger.exception("Failed to process Stripe webhook")
            msg = f"Failed to process webhook: {e}"
            raise WebhookProcessingError(
                msg,
                gateway=self.gateway_name,
                original_error=e,
            ) from e

    def cancel_payment(self, payment_id: str) -> PaymentResult:
        """Cancel a Stripe payment intent."""
        try:
            payment_intent = stripe.PaymentIntent.cancel(payment_id)
            logger.info("Stripe payment intent canceled successfully: %s", payment_id)
            return self._convert_stripe_payment_to_result(payment_intent)

        except stripe.StripeError as e:
            logger.exception("Stripe payment cancellation failed")
            msg = f"Failed to cancel payment: {self._get_stripe_error_message(e)}"
            raise PaymentGatewayError(
                msg,
                gateway=self.gateway_name,
                original_error=e,
            ) from e
        except Exception as e:
            logger.exception("Unexpected error during payment cancellation")
            msg = f"Unexpected error canceling payment: {e}"
            raise PaymentGatewayError(
                msg,
                gateway=self.gateway_name,
                original_error=e,
            ) from e

    def capture_payment(
        self,
        payment_id: str,
        amount: Decimal | None = None,
    ) -> PaymentResult:
        """Capture a Stripe payment intent."""
        try:
            capture_params: dict = {}
            if amount is not None:
                capture_params["amount_to_capture"] = int(amount * 100)

            payment_intent = stripe.PaymentIntent.capture(payment_id, **capture_params)
            logger.info("Stripe payment intent captured successfully: %s", payment_id)
            return self._convert_stripe_payment_to_result(payment_intent)

        except stripe.StripeError as e:
            logger.exception("Stripe payment capture failed")
            msg = f"Failed to capture payment: {self._get_stripe_error_message(e)}"
            raise PaymentGatewayError(
                msg,
                gateway=self.gateway_name,
                original_error=e,
            ) from e
        except Exception as e:
            logger.exception("Unexpected error during payment capture")
            msg = f"Unexpected error capturing payment: {e}"
            raise PaymentGatewayError(
                msg,
                gateway=self.gateway_name,
                original_error=e,
            ) from e

    def list_payment_methods(self, customer_id: str) -> list[dict]:
        """List payment methods for a Stripe customer."""
        try:
            payment_methods = stripe.PaymentMethod.list(customer=customer_id)
            logger.info(
                "Retrieved %d payment methods for customer %s",
                len(payment_methods.data),
                customer_id,
            )

            return [
                {
                    "id": pm.id,
                    "type": pm.type,
                    "card": pm.card.to_dict() if pm.card else None,
                    "created_at": datetime.fromtimestamp(
                        pm.created,
                        tz=UTC,
                    ).isoformat(),
                }
                for pm in payment_methods.data
            ]

        except stripe.StripeError as e:
            logger.exception("Failed to list payment methods")
            msg = f"Failed to list payment methods: {self._get_stripe_error_message(e)}"
            raise PaymentGatewayError(
                msg,
                gateway=self.gateway_name,
                original_error=e,
            ) from e
        except Exception as e:
            logger.exception("Unexpected error listing payment methods")
            msg = f"Unexpected error listing payment methods: {e}"
            raise PaymentGatewayError(
                msg,
                gateway=self.gateway_name,
                original_error=e,
            ) from e
