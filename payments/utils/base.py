"""Base abstract payment gateway class."""

import logging
from abc import ABC
from abc import abstractmethod
from decimal import Decimal

import stripe
from django.db import transaction

from core.users.models import User
from payments.models.payments import Payment
from payments.utils.types import CustomerData
from payments.utils.types import PaymentIntentData
from payments.utils.types import PaymentResult
from payments.utils.types import RefundData
from payments.utils.types import RefundResult
from payments.utils.types import WebhookEvent
from settings.models import StripeSetting

logger = logging.getLogger(__name__)


class BasePaymentGateway(ABC):
    """
    Abstract base class for payment gateway implementations.

    All payment gateway implementations must inherit from this class
    and implement all abstract methods to ensure a consistent interface.
    """

    def __init__(self) -> None:
        """Initialize the payment gateway."""
        self._validate_configuration()

    @property
    @abstractmethod
    def gateway_name(self) -> str:
        """Return the name of the payment gateway."""

    @abstractmethod
    def _validate_configuration(self) -> None:
        """
        Validate that all required configuration is present.

        Raises:
            PaymentConfigurationError: If configuration is invalid or missing.
        """

    @abstractmethod
    def create_payment_intent(self, payment_data: PaymentIntentData) -> PaymentResult:
        """
        Create a payment intent/transaction.

        Args:
            payment_data: Payment intent data including amount, currency, etc.

        Returns:
            PaymentResult: Standardized payment result.

        Raises:
            PaymentCreationError: If payment creation fails.
        """

    @abstractmethod
    def retrieve_payment(self, payment_id: str) -> PaymentResult:
        """
        Retrieve payment information by ID.

        Args:
            payment_id: The payment ID from the gateway.

        Returns:
            PaymentResult: Standardized payment result.

        Raises:
            PaymentRetrievalError: If retrieval fails.
        """

    @abstractmethod
    def create_refund(self, refund_data: RefundData) -> RefundResult:
        """
        Create a refund for a payment.

        Args:
            refund_data: Refund data including payment_id and amount.

        Returns:
            RefundResult: Standardized refund result.

        Raises:
            RefundError: If refund creation fails.
        """

    @abstractmethod
    def create_customer(self, customer_data: CustomerData) -> dict[str, str]:
        """
        Create a customer in the payment gateway.

        Args:
            customer_data: Customer information.

        Returns:
            dict: Dictionary containing at least 'id' key with customer ID.

        Raises:
            CustomerCreationError: If customer creation fails.
        """

    @abstractmethod
    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        secret: str | None = None,
    ) -> bool:
        """
        Verify webhook signature to ensure request is from the payment gateway.

        Args:
            payload: Raw request body as bytes.
            signature: Signature from webhook headers.
            secret: Optional webhook secret (uses configured secret if not provided).

        Returns:
            bool: True if signature is valid, False otherwise.

        Raises:
            WebhookVerificationError: If verification process fails.
        """

    @abstractmethod
    def process_webhook(self, payload: dict) -> WebhookEvent:
        """
        Process webhook payload and return standardized event data.

        Args:
            payload: Webhook payload from the payment gateway.

        Returns:
            WebhookEvent: Standardized webhook event data.

        Raises:
            WebhookProcessingError: If webhook processing fails.
        """

    def cancel_payment(self, payment_id: str) -> PaymentResult:
        """
        Cancel a payment (optional, not all gateways support this).

        Args:
            payment_id: The payment ID to cancel.

        Returns:
            PaymentResult: Updated payment result.

        Raises:
            NotImplementedError: If gateway doesn't support cancellation.
            PaymentGatewayError: If cancellation fails.
        """
        msg = f"{self.gateway_name} does not support payment cancellation"
        raise NotImplementedError(msg)

    def capture_payment(
        self,
        payment_id: str,
        amount: Decimal | None = None,
    ) -> PaymentResult:
        """
        Capture a previously authorized payment.

        Args:
            payment_id: The payment ID to capture.
            amount: Optional amount to capture (None for full amount).

        Returns:
            PaymentResult: Updated payment result.

        Raises:
            NotImplementedError: If gateway doesn't support capture.
            PaymentGatewayError: If capture fails.
        """
        msg = f"{self.gateway_name} does not support payment capture"
        raise NotImplementedError(msg)

    def list_payment_methods(self, customer_id: str) -> list[dict]:
        """
        List payment methods for a customer (optional, not all gateways support this).

        Args:
            customer_id: The customer ID.

        Returns:
            list: List of payment methods.

        Raises:
            NotImplementedError: If gateway doesn't support listing payment methods.
            PaymentGatewayError: If listing fails.
        """
        msg = f"{self.gateway_name} does not support listing payment methods"
        raise NotImplementedError(msg)


@transaction.atomic
def stripe_create_instagram_user_story_credits_payment(
    user_id: int,
    instagram_user_id: int,
    story_credit_quantity: int,
) -> Payment:
    """
    Create a payment for Instagram user story credits.
    """

    stripe_settings = StripeSetting.get_solo()
    stripe.api_key = stripe_settings.api_key

    try:
        user = User.objects.get(id=user_id)
    except Exception as e:
        msg = f"Failed to get user {user_id}: {e}"
        logger.exception(msg)
        raise Exception(msg) from e  # noqa: TRY002

    payment = Payment(
        user=user,
        reference_type=Payment.REFERENCE_STRIPE,
        amount=story_credit_quantity,
    )

    checkout_session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": "Instagram Auto Update User Story Credits",
                    },
                    "unit_amount": 1,
                },
                "quantity": story_credit_quantity,
            },
        ],
        mode="payment",
        success_url="https://yoursite.com/success",
        cancel_url="https://yoursite.com/cancel",
        metadata={
            "payment_id": payment.id,
            "user_id": user.id,
        },
    )

    payment.reference = checkout_session.id
    payment.reference_type = Payment.REFERENCE_STRIPE
    payment.url = checkout_session.url
    payment.raw_data = checkout_session.to_dict()
    payment.amount = checkout_session.amount_total / 100
    payment.save()

    return payment
