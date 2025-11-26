"""Type definitions for payment gateways."""

from decimal import Decimal
from enum import Enum
from typing import Any
from typing import TypedDict


class PaymentStatus(str, Enum):
    """Standard payment status across all gateways."""

    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


class Currency(str, Enum):
    """Supported currencies."""

    USD = "usd"
    EUR = "eur"
    GBP = "gbp"
    IDR = "idr"
    SGD = "sgd"
    MYR = "myr"
    THB = "thb"
    PHP = "php"
    VND = "vnd"


class PaymentMethod(str, Enum):
    """Payment method types."""

    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    E_WALLET = "e_wallet"
    QRIS = "qris"
    VIRTUAL_ACCOUNT = "virtual_account"
    OVER_THE_COUNTER = "over_the_counter"


class CustomerData(TypedDict, total=False):
    """Customer information for payment processing."""

    email: str
    name: str
    phone: str
    address: dict[str, str]
    metadata: dict[str, Any]


class PaymentIntentData(TypedDict, total=False):
    """Data for creating a payment intent/transaction."""

    amount: Decimal
    currency: str
    customer_id: str | None
    customer_data: CustomerData | None
    payment_method_types: list[str]
    description: str
    metadata: dict[str, Any]
    return_url: str | None
    callback_url: str | None


class PaymentResult(TypedDict):
    """Standardized payment result across all gateways."""

    id: str
    status: PaymentStatus
    amount: Decimal
    currency: str
    customer_id: str | None
    payment_method: str | None
    created_at: str
    metadata: dict[str, Any]
    gateway_response: dict[str, Any]  # Original gateway response


class RefundData(TypedDict, total=False):
    """Data for creating a refund."""

    payment_id: str
    amount: Decimal | None  # None for full refund
    reason: str | None
    metadata: dict[str, Any]


class RefundResult(TypedDict):
    """Standardized refund result."""

    id: str
    payment_id: str
    amount: Decimal
    currency: str
    status: str
    created_at: str
    reason: str | None
    gateway_response: dict[str, Any]


class WebhookEvent(TypedDict):
    """Standardized webhook event data."""

    event_type: str
    payment_id: str | None
    data: dict[str, Any]
    gateway_response: dict[str, Any]
