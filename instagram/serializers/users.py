from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from instagram.models import User as InstagramUser


class InstagramUserListSerializer(ModelSerializer):
    has_stories = serializers.BooleanField(read_only=True)
    has_history = serializers.BooleanField(read_only=True)

    class Meta:
        model = InstagramUser
        exclude = ["original_profile_picture_url", "raw_api_data"]


class InstagramUserDetailSerializer(ModelSerializer):
    has_stories = serializers.BooleanField(read_only=True)
    has_history = serializers.BooleanField(read_only=True)

    class Meta:
        model = InstagramUser
        fields = "__all__"
