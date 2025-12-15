from unittest.mock import Mock
from unittest.mock import patch

from celery.result import EagerResult
from django.test import TestCase
from django.test import override_settings

from instagram.models import User
from instagram.serializers.users import InstagramUserDetailSerializer
from instagram.serializers.users import InstagramUserListSerializer
from instagram.tasks import user_generate_blur_data_url
from instagram.tests.factories import InstagramUserFactory


class TestUserGenerateBlurDataUrl(TestCase):
    """Tests for the user_generate_blur_data_url Celery task."""

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.utils.generate_blur_data_url_from_image_url")
    def test_user_generate_blur_data_url_success(
        self,
        mock_generate_blur,
    ):
        """Test successful blur data URL generation and saving."""
        # Create a test user with a profile picture URL
        user = InstagramUserFactory(
            original_profile_picture_url="http://example.com/profile.jpg",
            blur_data_url="",
        )

        # Mock the utility function
        mock_generate_blur.return_value = "base64encodedstring"

        # Execute the task
        result = user_generate_blur_data_url.delay(user.uuid)

        # Verify the task executed successfully
        assert isinstance(result, EagerResult)
        assert result.result["success"] is True
        assert result.result["username"] == user.username

        # Verify the blur_data_url was saved to the model
        user.refresh_from_db()
        assert user.blur_data_url == "base64encodedstring"

        # Verify the utility function was called with correct URL
        mock_generate_blur.assert_called_once_with(
            "http://example.com/profile.jpg",
        )

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.utils.generate_blur_data_url_from_image_url")
    def test_user_generate_blur_data_url_fallback_to_profile_picture(
        self,
        mock_generate_blur,
    ):
        """Test fallback to profile_picture if original_url is missing."""
        # Create a test user with local profile picture but no original URL
        # Note: We mock the file field to return a URL
        user = InstagramUserFactory(
            original_profile_picture_url="",
            blur_data_url="",
        )
        # Mock profile_picture.url behavior
        user.profile_picture = Mock()
        user.profile_picture.url = "/media/users/profile.jpg"
        user.save()

        # Mock the utility function
        mock_generate_blur.return_value = "base64encodedstring"

        # Execute the task
        result = user_generate_blur_data_url.delay(user.uuid)

        # Verify success
        assert result.result["success"] is True

        # Verify called with local URL
        mock_generate_blur.assert_called_once_with("/media/users/profile.jpg")

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_user_generate_blur_data_url_no_picture(self):
        """Test when user has no picture at all."""
        user = InstagramUserFactory(
            original_profile_picture_url="",
            blur_data_url="",
        )
        # Ensure profile_picture is empty/falsey
        user.profile_picture = None
        user.save()

        # Execute the task
        result = user_generate_blur_data_url.delay(user.uuid)

        # Verify failure/info
        assert result.result["success"] is False
        assert "No profile picture URL" in result.result["error"]

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_user_generate_blur_data_url_user_not_found(self):
        """Test handling of non-existent user."""
        result = user_generate_blur_data_url.delay("nonexistent_uuid")
        assert result.result["success"] is False
        assert "not found" in result.result["error"].lower()

    def test_user_serializers_include_blur_data_url(self):
        """Test that serializers include the blur_data_url field."""
        user = InstagramUserFactory(
            username="testuser_serializer",
            blur_data_url="base64encodedblur",
        )

        # Test List Serializer
        list_serializer = InstagramUserListSerializer(user)
        assert "blur_data_url" in list_serializer.data
        assert list_serializer.data["blur_data_url"] == "base64encodedblur"

        # Test Detail Serializer
        detail_serializer = InstagramUserDetailSerializer(user)
        assert "blur_data_url" in detail_serializer.data
        assert detail_serializer.data["blur_data_url"] == "base64encodedblur"
