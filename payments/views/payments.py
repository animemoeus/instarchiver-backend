from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from payments.models import Payment
from payments.paginations import PaymentCursorPagination
from payments.serializers.payments import PaymentCreateSerializer
from payments.serializers.payments import PaymentListSerializer
from payments.utils import stripe_create_instagram_user_story_credits_payment


class PaymentListCreateAPIView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    pagination_class = PaymentCursorPagination
    ordering = ["-created_at"]

    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return PaymentCreateSerializer
        return PaymentListSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        using = serializer.validated_data.get("using")

        if using == Payment.REFERENCE_STRIPE:
            self.handle_stripe_payment(serializer)
        return Response("arter")

    def handle_stripe_payment(self, serializer: PaymentCreateSerializer):
        user = self.request.user
        type = serializer.validated_data.get("type")  # noqa: A001
        target = serializer.validated_data.get("target")
        quantity = serializer.validated_data.get("quantity")

        if type == Payment.TYPE_INSTAGRAM_USER_STORY_CREDIT:
            self.handle_instagram_user_story_credit(user, target, quantity)
        elif type == Payment.TYPE_INSTAGRAM_USER_PROFILE_CREDIT:
            self.handle_instagram_user_profile_credit(user, target, quantity)

    def handle_instagram_user_story_credit(self, user, target, quantity):
        stripe_create_instagram_user_story_credits_payment(
            user_id=user.id,
            instagram_user_id=target,
            story_credit_quantity=quantity,
        )

    def handle_instagram_user_profile_credit(self, user, target, quantity):
        pass
