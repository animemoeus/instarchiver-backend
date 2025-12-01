from rest_framework import serializers

from authentication.serializers import UserSerializer
from payments.models.payments import Payment


class PaymentListSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Payment
        fields = ["id", "amount", "status", "created_at", "user"]
