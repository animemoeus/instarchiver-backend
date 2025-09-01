from rest_framework import serializers


class RefreshTokenSerializer(serializers.Serializer):
    """Serializer for JWT token refresh."""

    refresh = serializers.CharField(help_text="Refresh token")


class LoginWithGoogleSerializer(serializers.Serializer):
    """Serializer for Google OAuth login with Firebase token."""

    token = serializers.CharField(
        max_length=2048,
        help_text="Firebase ID token from Google Sign-In",
    )

    def validate_token(self, value):
        """Validate that the Firebase token is not empty."""
        if not value.strip():
            msg = "Firebase token cannot be empty"
            raise serializers.ValidationError(msg)
        return value.strip()


class GoogleLoginResponseSerializer(serializers.Serializer):
    """Serializer for JWT token response."""

    refresh = serializers.CharField(read_only=True, help_text="Refresh JWT token")
    access = serializers.CharField(read_only=True, help_text="Access JWT token")


class UserInfoSerializer(serializers.Serializer):
    """Serializer for user information from Firebase."""

    uid = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    name = serializers.CharField(read_only=True)
    photo_url = serializers.URLField(read_only=True, allow_null=True)
