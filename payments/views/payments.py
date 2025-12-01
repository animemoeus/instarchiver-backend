from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import IsAuthenticated

from payments.models import Payment
from payments.serializers.payments import PaymentListSerializer


class PaymentListCreateAPIView(ListCreateAPIView):
    serializer_class = PaymentListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user)
