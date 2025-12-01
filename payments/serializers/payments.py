from rest_framework import serializers

from authentication.serializers import UserSerializer
from payments.models.payments import Payment


class PaymentListSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Payment
        fields = ["id", "amount", "status", "created_at", "user", "reference_type"]


class PaymentCreateSerializer(serializers.Serializer):
    reference_type = serializers.ChoiceField(choices=Payment.REFERENCE_CHOICES)
    type = serializers.ChoiceField(choices=Payment.TYPE_CHOICES)
    quantity = serializers.IntegerField(min_value=1)
