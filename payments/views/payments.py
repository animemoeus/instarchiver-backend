from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import IsAuthenticated

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
