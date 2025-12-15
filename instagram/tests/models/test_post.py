from unittest.mock import Mock
from unittest.mock import patch

from django.test import TestCase

from instagram.tests.factories import PostFactory
from instagram.tests.factories import PostMediaFactory


class TestPostModel(TestCase):
    """Tests for the Post model methods."""

    def test_post_creation(self):
        """Test that a Post instance can be created successfully."""
        post = PostFactory()

        assert post.id is not None
        assert post.user is not None
        assert post.variant in [post.POST_VARIANT_NORMAL, post.POST_VARIANT_CAUROSEL]
        assert post.thumbnail_url is not None
        assert post.created_at is not None
        assert post.updated_at is not None

    def test_post_str_representation(self):
        """Test the string representation of a Post instance."""
        post = PostFactory()
        expected_str = f"{post.user.username} - {post.id}"

        assert str(post) == expected_str

    def test_post_user_relationship(self):
        """Test that Post has a valid relationship with User."""
        post = PostFactory()

        assert post.user.username is not None
        assert post.user.instagram_id is not None

    @patch("instagram.tasks.post_generate_blur_data_url.delay")
    def test_generate_blur_data_url_task_queues_task(self, mock_task_delay):
        """Test that generate_blur_data_url_task queues a Celery task."""
        # Create a test post
        post = PostFactory()

        # Mock the task delay
        mock_result = Mock()
        mock_result.id = "task-id-123"
        mock_task_delay.return_value = mock_result

        # Call the method
        post.generate_blur_data_url_task()

        # Verify the task was queued
        mock_task_delay.assert_called_once()

    @patch("instagram.tasks.post_generate_blur_data_url.delay")
    def test_generate_blur_data_url_task_passes_post_id(
        self,
        mock_task_delay,
    ):
        """Test that generate_blur_data_url_task passes correct post id."""
        # Create a test post
        post = PostFactory()

        # Mock the task delay
        mock_result = Mock()
        mock_result.id = "task-id-123"
        mock_task_delay.return_value = mock_result

        # Call the method
        post.generate_blur_data_url_task()

        # Verify the task was called with the correct post id
        mock_task_delay.assert_called_once_with(post.id)

    @patch("instagram.tasks.post_generate_blur_data_url.delay")
    def test_generate_blur_data_url_task_multiple_calls(
        self,
        mock_task_delay,
    ):
        """Test multiple calls queue separate tasks."""
        # Create test posts
        post1 = PostFactory()
        post2 = PostFactory()

        # Mock the task delay
        mock_result = Mock()
        mock_result.id = "task-id-123"
        mock_task_delay.return_value = mock_result

        # Call the method on both posts
        post1.generate_blur_data_url_task()
        post2.generate_blur_data_url_task()

        # Verify the task was queued twice with different post ids
        assert mock_task_delay.call_count == 2  # noqa: PLR2004
        mock_task_delay.assert_any_call(post1.id)
        mock_task_delay.assert_any_call(post2.id)


class TestPostMediaModel(TestCase):
    """Tests for the PostMedia model."""

    def test_post_media_creation(self):
        """Test that a PostMedia instance can be created successfully."""
        post_media = PostMediaFactory()

        assert post_media.id is not None
        assert post_media.post is not None
        assert post_media.thumbnail_url is not None
        assert post_media.media_url is not None
        assert post_media.created_at is not None
        assert post_media.updated_at is not None

    def test_post_media_str_representation(self):
        """Test the string representation of a PostMedia instance."""
        post_media = PostMediaFactory()
        expected_str = f"{post_media.post.user.username} - {post_media.post.id}"

        assert str(post_media) == expected_str

    def test_post_media_post_relationship(self):
        """Test that PostMedia has a valid relationship with Post."""
        post_media = PostMediaFactory()

        assert post_media.post.id is not None
        assert post_media.post.user is not None
        assert post_media.post.variant is not None
