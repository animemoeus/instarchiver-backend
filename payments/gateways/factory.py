from payments.gateways.base import PaymentGatewayBase
from payments.gateways.stripe import StripePaymentGateway
from payments.models.payments import Payment


class PaymentGatewayFactory:
    """Factory to get the appropriate payment gateway."""

    _gateways: dict[str, type[PaymentGatewayBase]] = {
        Payment.REFERENCE_STRIPE: StripePaymentGateway,
        # Add more gateways here:
        # Payment.REFERENCE_PAYPAL: PayPalPaymentGateway,
    }

    @classmethod
    def get_gateway(cls, reference_type: str) -> PaymentGatewayBase:
        """
        Get payment gateway instance by reference type.

        Args:
            reference_type: Payment reference type (e.g., Payment.REFERENCE_STRIPE)

        Returns:
            PaymentGatewayBase: Instance of the payment gateway

        Raises:
            ValueError: If gateway is not supported
        """
        gateway_class = cls._gateways.get(reference_type)

        if not gateway_class:
            msg = f"Unsupported payment gateway: {reference_type}"
            raise ValueError(msg)

        return gateway_class()

    @classmethod
    def register_gateway(
        cls,
        reference_type: str,
        gateway_class: type[PaymentGatewayBase],
    ):
        """
        Register a new payment gateway (useful for plugins/extensions).

        Args:
            reference_type: Payment reference type identifier
            gateway_class: Gateway class implementing PaymentGatewayBase
        """
        cls._gateways[reference_type] = gateway_class
