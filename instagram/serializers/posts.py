from rest_framework import serializers

from instagram.models import Post
from instagram.models import PostMedia
from instagram.serializers.users import InstagramUserDetailSerializer
from instagram.serializers.users import InstagramUserListSerializer


class PostMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostMedia
        fields = [
            "id",
            "thumbnail_url",
            "media_url",
            "thumbnail",
            "media",
            "created_at",
            "updated_at",
        ]


class PostListSerializer(serializers.ModelSerializer):
    user = InstagramUserListSerializer(read_only=True)
    media_count = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id",
            "variant",
            "thumbnail_url",
            "thumbnail",
            "blur_data_url",
            "media_count",
            "created_at",
            "updated_at",
            "user",
        ]

    def get_media_count(self, obj):
        """Return the count of media items for this post."""
        return obj.media_count


class PostDetailSerializer(serializers.ModelSerializer):
    user = InstagramUserDetailSerializer(read_only=True)
    media = PostMediaSerializer(source="postmedia_set", many=True, read_only=True)

    class Meta:
        model = Post
        fields = [
            "id",
            "variant",
            "thumbnail_url",
            "thumbnail",
            "blur_data_url",
            "media",
            "created_at",
            "updated_at",
            "user",
        ]
