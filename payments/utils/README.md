# Payment Gateway Utilities

A flexible, ABC-based payment gateway system that supports multiple payment providers with a consistent interface.

## Architecture

The payment utilities follow an Abstract Base Class (ABC) pattern that allows for easy integration of multiple payment gateways:

- **[base.py](base.py)**: Abstract base class defining the payment gateway interface
- **[stripe.py](stripe.py)**: Stripe payment gateway implementation
- **[factory.py](factory.py)**: Factory pattern for creating gateway instances
- **[types.py](types.py)**: TypedDict definitions for type safety
- **[exceptions.py](exceptions.py)**: Custom exception classes

## Quick Start

### Using the Factory

```python
from payments.utils import PaymentGatewayFactory, PaymentGatewayType

# Create a Stripe gateway instance
gateway = PaymentGatewayFactory.create_gateway(PaymentGatewayType.STRIPE)

# Or use string
gateway = PaymentGatewayFactory.create_gateway("stripe")
```

### Creating a Payment

```python
from decimal import Decimal
from payments.utils import PaymentGatewayFactory, PaymentIntentData

gateway = PaymentGatewayFactory.create_gateway("stripe")

payment_data = PaymentIntentData(
    amount=Decimal("99.99"),
    currency="usd",
    description="Premium subscription",
    metadata={"user_id": "12345"},
)

result = gateway.create_payment_intent(payment_data)
print(f"Payment created: {result['id']}")
print(f"Status: {result['status']}")
```

### Retrieving a Payment

```python
payment_id = "pi_1234567890"
result = gateway.retrieve_payment(payment_id)
print(f"Payment status: {result['status']}")
print(f"Amount: {result['amount']} {result['currency']}")
```

### Creating a Refund

```python
from payments.utils import RefundData

refund_data = RefundData(
    payment_id="pi_1234567890",
    reason="requested_by_customer",
)

refund_result = gateway.create_refund(refund_data)
print(f"Refund created: {refund_result['id']}")
```

### Handling Webhooks

```python
# In your Django view
from django.http import HttpResponse
from payments.utils import PaymentGatewayFactory

def stripe_webhook(request):
    gateway = PaymentGatewayFactory.create_gateway("stripe")

    payload = request.body
    signature = request.META.get("HTTP_STRIPE_SIGNATURE")

    # Verify the webhook signature
    if not gateway.verify_webhook_signature(payload, signature):
        return HttpResponse(status=400)

    # Process the webhook
    import json
    event = gateway.process_webhook(json.loads(payload))

    if event["event_type"] == "payment_intent.succeeded":
        payment_id = event["payment_id"]
        # Handle successful payment
        print(f"Payment succeeded: {payment_id}")

    return HttpResponse(status=200)
```

## Configuration

Payment gateway credentials are stored in database singleton models (following the project's pattern):

### Stripe Configuration

Configure Stripe through Django admin or programmatically:

```python
from settings.models import StripeSetting

settings = StripeSetting.get_solo()
settings.api_key = "sk_test_..."
settings.webhook_secret = "whsec_..."
settings.save()
```

## Adding New Gateways

To add support for a new payment gateway (e.g., Xendit):

1. **Create the implementation**:

```python
# payments/utils/xendit.py
from payments.utils.base import BasePaymentGateway
from payments.utils.types import PaymentIntentData, PaymentResult

class XenditPaymentGateway(BasePaymentGateway):
    @property
    def gateway_name(self) -> str:
        return "xendit"

    def _validate_configuration(self) -> None:
        # Validate Xendit settings
        pass

    def create_payment_intent(self, payment_data: PaymentIntentData) -> PaymentResult:
        # Implement Xendit payment creation
        pass

    # Implement other abstract methods...
```

2. **Register in factory** (automatic):

The factory automatically registers gateways on import. Just add:

```python
# payments/utils/factory.py
try:
    from payments.utils.xendit import XenditPaymentGateway
    PaymentGatewayFactory.register_gateway("xendit", XenditPaymentGateway)
except ImportError:
    pass
```

3. **Create settings model**:

```python
# settings/models.py
class XenditSetting(SingletonModel):
    api_key = models.CharField(max_length=255)
    webhook_secret = models.CharField(max_length=255)
```

## Available Gateways

Check which gateways are available:

```python
from payments.utils import PaymentGatewayFactory

available = PaymentGatewayFactory.get_available_gateways()
print(f"Available gateways: {available}")
# Output: ['stripe']  (more will be added when dependencies are installed)
```

## Type Safety

All data structures use TypedDict for type safety:

```python
from payments.utils.types import (
    PaymentStatus,
    Currency,
    PaymentIntentData,
    PaymentResult,
    CustomerData,
)

# IDE will provide autocomplete and type checking
payment_data: PaymentIntentData = {
    "amount": Decimal("99.99"),
    "currency": Currency.USD,  # Enum for currencies
}
```

## Error Handling

All exceptions inherit from `PaymentGatewayError`:

```python
from payments.utils.exceptions import (
    PaymentConfigurationError,
    PaymentCreationError,
    PaymentRetrievalError,
    RefundError,
    WebhookVerificationError,
)

try:
    result = gateway.create_payment_intent(payment_data)
except PaymentConfigurationError as e:
    print(f"Configuration error: {e}")
    print(f"Gateway: {e.gateway}")
except PaymentCreationError as e:
    print(f"Payment creation failed: {e}")
    print(f"Original error: {e.original_error}")
```

## Testing

Run tests with pytest:

```bash
just django pytest payments/tests/
```

## Future Enhancements

When ready to add Xendit, Midtrans, or other gateways:

1. Install the gateway's Python SDK
2. Create the implementation file
3. Add the settings model
4. The factory will automatically register it

The ABC ensures all gateways provide a consistent interface.
