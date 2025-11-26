from django.core.files.storage import default_storage
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from instagram.models import User as InstagramUser


class InstagramUserCreateSerializer(serializers.Serializer):
    """Serializer for creating Instagram users with username only."""

    username = serializers.CharField()

    def validate_username(self, value):
        if InstagramUser.objects.filter(username=value).exists():
            msg = "User with this username already exists."
            raise serializers.ValidationError(msg)
        return value

    def create(self, validated_data):
        username = validated_data["username"]
        instagram_user = InstagramUser.objects.create(username=username)
        instagram_user.update_profile_from_api()
        return instagram_user


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
        exclude = ["raw_api_data"]
        extra_kwargs = {
            "api_updated_at": {"write_only": True},
        }

    def get_auto_update_stories_limit_count(self, obj):
        """Return the count of story update limits (placeholder for now)."""
        return 0

    def get_auto_update_profile_limit_count(self, obj):
        """Return the count of profile update limits (placeholder for now)."""
        return 0


class InstagramUserHistoryListSerializer(ModelSerializer):
    """Serializer for historical Instagram user records."""

    history_id = serializers.IntegerField(read_only=True)
    history_date = serializers.DateTimeField(read_only=True)
    history_change_reason = serializers.CharField(read_only=True, allow_null=True)
    history_type = serializers.CharField(read_only=True)
    profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = InstagramUser.history.model
        exclude = ["original_profile_picture_url", "raw_api_data", "history_user"]

    def get_profile_picture(self, obj):
        """Return the full URL for the profile picture if it exists.

        Note: django-simple-history stores file fields as strings (file paths),
        not as FieldFile objects, so we need to use the storage backend to
        construct the full URL.
        """
        if obj.profile_picture:
            # Historical records store the file path as a string
            return default_storage.url(obj.profile_picture)
        return None
