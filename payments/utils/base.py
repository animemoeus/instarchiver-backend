import logging
import warnings
from datetime import timedelta

import stripe
from django.db import transaction
from django.utils import timezone

from core.users.models import User
from payments.models.payments import Payment
from settings.models import StripeSetting

logger = logging.getLogger(__name__)


@transaction.atomic
def stripe_create_instagram_user_story_credits_payment(
    user_id: int,
    instagram_user_id: int,
    story_credit_quantity: int,
) -> Payment:
    """
    Create a payment for Instagram user story credits.

    .. deprecated::
        This function is deprecated. Use the gateway architecture instead:

        from payments.gateways.factory import PaymentGatewayFactory
        gateway = PaymentGatewayFactory.get_gateway(Payment.REFERENCE_STRIPE)
        payment_data = gateway.create_checkout_session(
            user_id=user_id,
            payment_type=Payment.TYPE_INSTAGRAM_USER_STORY_CREDIT,
            target=instagram_user_id,
            quantity=story_credit_quantity,
        )
    """
    warnings.warn(
        "stripe_create_instagram_user_story_credits_payment is deprecated. "
        "Use PaymentGatewayFactory instead.",
        DeprecationWarning,
        stacklevel=2,
    )

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
                        "name": f"Instagram Auto Update User Story Credits (x{story_credit_quantity})",  # noqa: E501
                    },
                    "unit_amount": 1,
                },
                "quantity": story_credit_quantity,
            },
        ],
        mode="payment",
        success_url="https://instarchiver.com/success",
        cancel_url="https://instarchiver.com/cancel",
        metadata={
            "user_id": user.id,
            "instagram_user_id": instagram_user_id,
            "story_credit_quantity": story_credit_quantity,
        },
        expires_at=timezone.localdate() + timedelta(hours=1),
    )

    payment.reference = checkout_session.id
    payment.reference_type = Payment.REFERENCE_STRIPE
    payment.url = checkout_session.url
    payment.raw_data = checkout_session.to_dict()
    payment.amount = checkout_session.amount_total / 100
    payment.save()

    return payment
