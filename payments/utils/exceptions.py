"""Payment gateway exceptions."""


class PaymentGatewayError(Exception):
    """Base exception for all payment gateway errors."""

    def __init__(
        self,
        message: str,
        gateway: str | None = None,
        original_error: Exception | None = None,
    ) -> None:
        self.gateway = gateway
        self.original_error = original_error
        super().__init__(message)


class PaymentConfigurationError(PaymentGatewayError):
    """Raised when payment gateway configuration is invalid or missing."""


class PaymentCreationError(PaymentGatewayError):
    """Raised when payment creation fails."""


class PaymentRetrievalError(PaymentGatewayError):
    """Raised when retrieving payment information fails."""


class RefundError(PaymentGatewayError):
    """Raised when refund operation fails."""


class CustomerCreationError(PaymentGatewayError):
    """Raised when customer creation fails."""


class WebhookVerificationError(PaymentGatewayError):
    """Raised when webhook signature verification fails."""


class WebhookProcessingError(PaymentGatewayError):
    """Raised when processing webhook data fails."""
