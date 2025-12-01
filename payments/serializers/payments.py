from rest_framework import serializers

from authentication.serializers import UserSerializer
from instagram.models import User as InstagramUser
from payments.models.payments import Payment


class PaymentListSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Payment
        fields = ["id", "amount", "status", "created_at", "user", "reference_type"]


class PaymentCreateSerializer(serializers.Serializer):
    reference_type = serializers.ChoiceField(choices=Payment.REFERENCE_CHOICES)
    type = serializers.ChoiceField(choices=Payment.TYPE_CHOICES)
    target = serializers.CharField()
    quantity = serializers.IntegerField(min_value=1)

    def validate(self, data):
        payment_type = data.get("type")
        target = data.get("target")

        if payment_type in (
            Payment.TYPE_INSTAGRAM_USER_STORY_CREDIT,
            Payment.TYPE_INSTAGRAM_USER_PROFILE_CREDIT,
        ):
            if not InstagramUser.objects.filter(uuid=target).exists():
                raise serializers.ValidationError(
                    {
                        "target": "Instagram user not found",
                    },
                )

        return data
