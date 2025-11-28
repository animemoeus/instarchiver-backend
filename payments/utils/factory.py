"""Payment gateway factory for creating gateway instances."""

from enum import Enum

from payments.utils.base import BasePaymentGateway
from payments.utils.exceptions import PaymentConfigurationError


class PaymentGatewayType(str, Enum):
    """Available payment gateway types."""

    STRIPE = "stripe"
    XENDIT = "xendit"
    MIDTRANS = "midtrans"


class PaymentGatewayFactory:
    """Factory class for creating payment gateway instances."""

    _gateways: dict[str, type[BasePaymentGateway]] = {}

    @classmethod
    def register_gateway(
        cls,
        gateway_type: str,
        gateway_class: type[BasePaymentGateway],
    ) -> None:
        """
        Register a new payment gateway implementation.

        Args:
            gateway_type: The gateway type identifier (e.g., 'stripe', 'xendit').
            gateway_class: The gateway class that extends BasePaymentGateway.
        """
        cls._gateways[gateway_type.lower()] = gateway_class

    @classmethod
    def create_gateway(cls, gateway_type: str) -> BasePaymentGateway:
        """
        Create a payment gateway instance.

        Args:
            gateway_type: The type of gateway to create
                        (e.g., 'stripe', 'xendit', 'midtrans').

        Returns:
            BasePaymentGateway: An instance of the requested payment gateway.

        Raises:
            PaymentConfigurationError: If gateway type is not registered.
        """
        gateway_class = cls._gateways.get(gateway_type.lower())

        if not gateway_class:
            available = ", ".join(cls._gateways.keys())
            msg = (
                f"Payment gateway '{gateway_type}' is not registered. "
                f"Available gateways: {available}"
            )
            raise PaymentConfigurationError(msg, gateway=gateway_type)

        return gateway_class()

    @classmethod
    def get_available_gateways(cls) -> list[str]:
        """
        Get a list of all registered gateway types.

        Returns:
            list: List of registered gateway type identifiers.
        """
        return list(cls._gateways.keys())


# Auto-register Stripe gateway
try:
    from payments.utils.stripe import StripePaymentGateway

    PaymentGatewayFactory.register_gateway(
        PaymentGatewayType.STRIPE,
        StripePaymentGateway,
    )
except ImportError:
    pass

# Auto-register Xendit gateway when available
try:
    from payments.utils.xendit import (
        XenditPaymentGateway,  # type: ignore[import-not-found]
    )

    PaymentGatewayFactory.register_gateway(
        PaymentGatewayType.XENDIT,
        XenditPaymentGateway,
    )
except ImportError:
    pass

# Auto-register Midtrans gateway when available
try:
    from payments.utils.midtrans import (
        MidtransPaymentGateway,  # type: ignore[import-not-found]
    )

    PaymentGatewayFactory.register_gateway(
        PaymentGatewayType.MIDTRANS,
        MidtransPaymentGateway,
    )
except ImportError:
    pass
