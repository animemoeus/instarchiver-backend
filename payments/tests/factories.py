import factory
from factory import Faker
from factory import SubFactory
from factory.django import DjangoModelFactory

from core.users.tests.factories import UserFactory
from payments.models import Payment


class PaymentFactory(DjangoModelFactory):
    user = SubFactory(UserFactory)
    reference_type = Payment.REFERENCE_STRIPE
    reference = Faker("uuid4")
    url = Faker("url")
    status = Payment.STATUS_UNPAID
    amount = Faker("pydecimal", left_digits=5, right_digits=2, positive=True)
    raw_data = factory.LazyFunction(
        lambda: {
            "id": factory.Faker("uuid4").evaluate(None, None, extra={"locale": None}),
            "object": "checkout.session",
            "payment_status": "unpaid",
            "amount_total": 1000,
            "currency": "usd",
        },
    )

    class Meta:
        model = Payment
        django_get_or_create = ["reference"]
