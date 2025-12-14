from rest_framework import serializers

from authentication.serializers import UserSerializer
from instagram.models import User as InstagramUser
from payments.models import GatewayOption
from payments.models import Payment


class PaymentListSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Payment
        fields = ["id", "amount", "status", "created_at", "user", "reference_type"]


class PaymentCreateSerializer(serializers.Serializer):
    payment_gateway = serializers.ChoiceField(choices=Payment.REFERENCE_CHOICES)
    payment_type = serializers.ChoiceField(choices=Payment.TYPE_CHOICES)
    instagram_user_id = serializers.CharField()
    quantity = serializers.IntegerField(min_value=1)

    def validate(self, data):
        payment_type = data.get("payment_type")
        instagram_user_id = data.get("instagram_user_id")

        if payment_type in (
            Payment.TYPE_INSTAGRAM_USER_STORY_CREDIT,
            Payment.TYPE_INSTAGRAM_USER_PROFILE_CREDIT,
        ):
            if not InstagramUser.objects.filter(uuid=instagram_user_id).exists():
                raise serializers.ValidationError(
                    {
                        "instagram_user_id": "Instagram user not found",
                    },
                )

        return data

    def validate_payment_gateway(self, value):
        if not GatewayOption.objects.filter(name=value, is_active=True).exists():
            msg = "Gateway option not found"
            raise serializers.ValidationError(msg)

        return value


class GatewayOptionsListSerializer(serializers.ModelSerializer):
    class Meta:
        model = GatewayOption
        fields = [
            "id",
            "name",
        ]
