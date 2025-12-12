import logging
from decimal import Decimal
from typing import Any

import stripe

from core.users.models import User
from payments.gateways.base import PaymentGatewayBase
from payments.models.payments import Payment
from settings.models import StripeSetting

logger = logging.getLogger(__name__)


class StripePaymentGateway(PaymentGatewayBase):
    """Stripe payment gateway implementation."""

    def __init__(self):
        """Initialize Stripe with API key from settings."""
        stripe_settings = StripeSetting.get_solo()
        if not stripe_settings.api_key:
            msg = "Stripe API key is not configured"
            raise ValueError(msg)
        stripe.api_key = stripe_settings.api_key
        self.webhook_secret = stripe_settings.webhook_secret
        self.success_url = stripe_settings.success_url
        self.cancel_url = stripe_settings.cancel_url

    def create_checkout_session(
        self,
        user_id: int,
        payment_type: str,
        target: str,
        quantity: int,
        **kwargs,
    ) -> dict[str, Any]:
        """Create a Stripe checkout session."""

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist as e:
            msg = f"User {user_id} not found"
            logger.exception(msg)
            raise ValueError(msg) from e

        # Build line items based on payment type
        line_items = self._build_line_items(payment_type, quantity)

        # Build metadata
        metadata = {
            "user_id": user.id,
            "payment_type": payment_type,
            "target": target,
            "quantity": quantity,
        }

        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=line_items,
            mode="payment",
            success_url=kwargs.get("success_url", self.success_url),
            cancel_url=kwargs.get("cancel_url", self.cancel_url),
            metadata=metadata,
        )

        return {
            "reference": checkout_session.id,
            "url": checkout_session.url,
            "amount": Decimal(checkout_session.amount_total) / 100,
            "raw_data": checkout_session.to_dict(),
        }

    def retrieve_payment_status(self, reference: str) -> dict[str, Any]:
        """Retrieve payment status from Stripe."""

        session = stripe.checkout.Session.retrieve(reference)

        return {
            "status": session.payment_status,  # Maps to Payment.STATUS_*
            "raw_data": session.to_dict(),
            "metadata": session.metadata,
        }

    def validate_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Validate Stripe webhook signature."""

        if not self.webhook_secret:
            msg = "Stripe webhook secret is not configured"
            raise ValueError(msg)

        try:
            stripe.Webhook.construct_event(
                payload=payload,
                sig_header=signature,
                secret=self.webhook_secret,
            )
            return True  # noqa: TRY300
        except stripe.error.SignatureVerificationError as e:
            logger.warning("Stripe webhook signature validation failed: %s", str(e))
            return False
        except Exception:
            logger.exception("Unexpected error during Stripe webhook signature validation")
            return False

    def process_webhook_event(self, event_data: dict[str, Any]) -> dict[str, Any]:
        """Process Stripe webhook event."""

        event_type = event_data.get("type")
        data_object = event_data.get("data", {}).get("object", {})

        return {
            "event_type": event_type,
            "reference": data_object.get("id"),
            "status": data_object.get("payment_status"),
            "metadata": data_object.get("metadata", {}),
        }

    def get_gateway_name(self) -> str:
        """Return gateway name."""
        return Payment.REFERENCE_STRIPE

    def _build_line_items(self, payment_type: str, quantity: int) -> list:
        """Build Stripe line items based on payment type."""

        if payment_type == Payment.TYPE_INSTAGRAM_USER_STORY_CREDIT:
            product_name = f"Instagram Auto Update User Story Credits (x{quantity})"
        elif payment_type == Payment.TYPE_INSTAGRAM_USER_PROFILE_CREDIT:
            product_name = f"Instagram User Profile Credits (x{quantity})"
        else:
            msg = f"Unknown payment type: {payment_type}"
            raise ValueError(msg)

        return [
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": product_name,
                    },
                    "unit_amount": 1,  # Price in cents
                },
                "quantity": quantity,
            },
        ]
