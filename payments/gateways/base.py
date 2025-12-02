from abc import ABC
from abc import abstractmethod
from typing import Any


class PaymentGatewayBase(ABC):
    """
    Abstract base class for payment gateway implementations.
    All payment gateways must implement these methods.
    """

    @abstractmethod
    def create_checkout_session(
        self,
        user_id: int,
        payment_type: str,
        target: str,
        quantity: int,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Create a checkout session and return payment data.

        Args:
            user_id: ID of the user making the payment
            payment_type: Type of payment (e.g., Payment.TYPE_INSTAGRAM_USER_STORY_CREDIT)
            target: Target identifier (e.g., Instagram user ID)
            quantity: Quantity of items being purchased
            **kwargs: Additional gateway-specific parameters

        Returns:
            Dict containing:
                - reference: Unique payment reference/ID from the gateway
                - url: Checkout URL for the user
                - amount: Total amount (Decimal)
                - raw_data: Full response from gateway (dict)

        Raises:
            ValueError: If user not found or invalid parameters
            Exception: If gateway API call fails
        """  # noqa: E501

    @abstractmethod
    def retrieve_payment_status(self, reference: str) -> dict[str, Any]:
        """
        Retrieve payment status from the gateway.

        Args:
            reference: Unique payment reference/ID

        Returns:
            Dict containing:
                - status: Payment status (mapped to Payment.STATUS_*)
                - raw_data: Full response from gateway (dict)
                - metadata: Additional metadata (dict)

        Raises:
            Exception: If gateway API call fails
        """

    @abstractmethod
    def validate_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """
        Validate webhook signature from the gateway.

        Args:
            payload: Raw webhook payload (bytes)
            signature: Signature header from the webhook request

        Returns:
            bool: True if signature is valid, False otherwise

        Raises:
            ValueError: If webhook secret is not configured
        """

    @abstractmethod
    def process_webhook_event(self, event_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process webhook event and extract relevant information.

        Args:
            event_data: Raw webhook event data

        Returns:
            Dict containing:
                - event_type: Type of event (str)
                - reference: Payment reference (str)
                - status: Payment status (str, optional)
                - metadata: Additional metadata (dict)
        """

    @abstractmethod
    def get_gateway_name(self) -> str:
        """
        Return the name of the payment gateway.

        Returns:
            str: Gateway name (e.g., Payment.REFERENCE_STRIPE)
        """
