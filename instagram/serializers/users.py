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
    auto_update_stories_limit_count = serializers.SerializerMethodField()
    auto_update_profile_limit_count = serializers.SerializerMethodField()
    updated_at_from_api = serializers.DateTimeField(
        source="api_updated_at",
        read_only=True,
    )

    class Meta:
        model = InstagramUser
        exclude = ["original_profile_picture_url", "raw_api_data"]
        extra_kwargs = {
            "api_updated_at": {"write_only": True},
        }

    def get_auto_update_stories_limit_count(self, obj):
        """Return the count of story update limits (placeholder for now)."""
        return 0

    def get_auto_update_profile_limit_count(self, obj):
        """Return the count of profile update limits (placeholder for now)."""
        return 0
