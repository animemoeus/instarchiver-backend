import stripe  # noqa: INP001

from core.users.models import User
from payments.models import Payment
from settings.models import StripeSetting


def run():
    stripe_settings = StripeSetting.get_solo()

    stripe.api_key = stripe_settings.api_key

    user = User.objects.first()
    amount = 1 * 100

    payment = Payment(
        user=user,  # Replace with the actual user instance
        reference_type=Payment.REFERENCE_STRIPE,
        status=Payment.STATUS_UNPAID,
        amount=amount,
    )

    checkout_session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": "Update User Profile Credit",
                    },
                    "unit_amount": 1,
                },
                "quantity": 100,
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
    payment.save()
