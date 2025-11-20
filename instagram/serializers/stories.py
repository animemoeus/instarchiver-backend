from rest_framework import serializers

from instagram.models import Story
from instagram.serializers.users import InstagramUserListSerializer


class StoryListSerializer(serializers.ModelSerializer):
    user = InstagramUserListSerializer(read_only=True)

    class Meta:
        model = Story
        fields = [
            "story_id",
            "user",
            "thumbnail",
            "media",
            "created_at",
            "story_created_at",
        ]
