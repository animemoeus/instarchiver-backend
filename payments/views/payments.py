from rest_framework import status
from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from payments.gateways.factory import PaymentGatewayFactory
from payments.models import Payment
from payments.paginations import PaymentCursorPagination
from payments.serializers.payments import PaymentCreateSerializer
from payments.serializers.payments import PaymentListSerializer


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
        """Create a new payment using the specified gateway."""

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Extract validated data
        gateway_type = serializer.validated_data.get("using")
        payment_type = serializer.validated_data.get("type")
        target = serializer.validated_data.get("target")
        quantity = serializer.validated_data.get("quantity")

        try:
            # Get the appropriate payment gateway
            gateway = PaymentGatewayFactory.get_gateway(gateway_type)

            # Create checkout session
            payment_data = gateway.create_checkout_session(
                user_id=request.user.id,
                payment_type=payment_type,
                target=target,
                quantity=quantity,
            )

            # Create payment record
            payment = Payment.objects.create(
                user=request.user,
                reference_type=gateway_type,
                reference=payment_data["reference"],
                url=payment_data["url"],
                amount=payment_data["amount"],
                type=payment_type,
                raw_data=payment_data["raw_data"],
            )

            return Response(
                {
                    "id": payment.id,
                    "url": payment.url,
                    "reference": payment.reference,
                    "amount": str(payment.amount),
                },
                status=status.HTTP_201_CREATED,
            )

        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception:  # noqa: BLE001
            return Response(
                {"error": "Failed to create payment"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
