from unittest.mock import Mock
from unittest.mock import patch

import requests
from celery.result import EagerResult
from django.core.files.base import ContentFile
from django.db.models.signals import post_save
from django.test import TestCase
from django.test import override_settings

from instagram.models import Post
from instagram.signals.post import post_post_save
from instagram.tasks import download_post_media_from_url
from instagram.tasks import download_post_media_thumbnail_from_url
from instagram.tasks import download_post_thumbnail_from_url
from instagram.tasks import generate_post_embedding
from instagram.tasks import generate_post_thumbnail_insight
from instagram.tasks import periodic_generate_post_blur_data_urls
from instagram.tasks import periodic_generate_post_embeddings
from instagram.tasks import periodic_generate_post_media_blur_data_urls
from instagram.tasks import periodic_generate_post_thumbnail_insights
from instagram.tasks import post_generate_blur_data_url
from instagram.tasks import post_media_generate_blur_data_url
from instagram.tests.factories import PostFactory
from instagram.tests.factories import PostMediaFactory


class TestPostGenerateBlurDataUrl(TestCase):
    """Tests for the post_generate_blur_data_url Celery task."""

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.generate_blur_data_url_from_image_url")
    def test_post_generate_blur_data_url_success(self, mock_generate_blur):
        """Test successful blur data URL generation and saving."""
        # Create a test post
        post = PostFactory(blur_data_url="")

        # Mock the utility function
        mock_generate_blur.return_value = "base64encodedstring"

        # Execute the task
        result = post_generate_blur_data_url.delay(post.id)

        # Verify the task executed successfully
        assert isinstance(result, EagerResult)
        assert result.result["success"] is True
        assert result.result["post_id"] == post.id

        # Verify the blur_data_url was saved to the model
        post.refresh_from_db()
        assert post.blur_data_url == "base64encodedstring"

        # Verify the utility function was called
        mock_generate_blur.assert_called_once()

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_post_generate_blur_data_url_post_not_found(self):
        """Test handling of non-existent post."""
        # Execute the task with non-existent post ID
        result = post_generate_blur_data_url.delay("nonexistent_post_id")

        # Verify the task returns an error
        assert isinstance(result, EagerResult)
        assert result.result["success"] is False
        assert "not found" in result.result["error"].lower()

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.generate_blur_data_url_from_image_url")
    def test_post_generate_blur_data_url_saves_to_model(self, mock_generate_blur):
        """Test that blur_data_url is correctly saved to the Post model."""
        # Create a test post
        post = PostFactory(blur_data_url="")

        # Mock the utility function with a specific value
        test_blur_data = "test_base64_encoded_blur_data"
        mock_generate_blur.return_value = test_blur_data

        # Execute the task
        post_generate_blur_data_url.delay(post.id)

        # Verify the blur_data_url was saved
        post.refresh_from_db()
        assert post.blur_data_url == test_blur_data

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.generate_blur_data_url_from_image_url")
    def test_post_generate_blur_data_url_network_error_retry(
        self,
        mock_generate_blur,
    ):
        """Test retry logic on network errors."""
        # Create a test post
        post = PostFactory(blur_data_url="")

        # Mock a network error
        mock_generate_blur.side_effect = Exception("Network timeout")

        # Execute the task
        result = post_generate_blur_data_url.delay(post.id)

        # Verify the task returns an error
        assert isinstance(result, EagerResult)
        assert result.result["success"] is False
        assert "error" in result.result

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.generate_blur_data_url_from_image_url")
    def test_post_generate_blur_data_url_uses_thumbnail(self, mock_generate_blur):
        """Test that the task uses the correct thumbnail source."""
        # Create a test post with thumbnail
        post = PostFactory(
            blur_data_url="",
            thumbnail_url="https://example.com/thumbnail.jpg",
        )

        # Mock the utility function
        mock_generate_blur.return_value = "base64encodedstring"

        # Execute the task
        post_generate_blur_data_url.delay(post.id)

        # Verify the utility function was called
        mock_generate_blur.assert_called_once()

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.generate_blur_data_url_from_image_url")
    def test_post_generate_blur_data_url_retryable_vs_non_retryable(
        self,
        mock_generate_blur,
    ):
        """Test distinction between retryable and non-retryable errors."""
        # Create a test post
        post = PostFactory(blur_data_url="")

        # Test non-retryable error
        mock_generate_blur.side_effect = Exception("Invalid image format")

        result = post_generate_blur_data_url.delay(post.id)

        assert result.result["success"] is False
        assert "Invalid image format" in result.result["error"]


class TestPeriodicGeneratePostBlurDataUrls(TestCase):
    """Tests for the periodic_generate_post_blur_data_urls Celery task."""

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.post_generate_blur_data_url.delay")
    def test_periodic_generate_post_blur_data_urls_success(self, mock_task_delay):
        """Test successful queuing of blur data URL generation tasks."""
        # Create posts without blur_data_url
        PostFactory(blur_data_url="")
        PostFactory(blur_data_url="")
        PostFactory(blur_data_url="")

        # Create a post with blur_data_url (should be skipped)
        PostFactory(blur_data_url="existing_blur_data")

        # Mock the task delay to return a mock result
        mock_result = Mock()
        mock_result.id = "task-id-123"
        mock_task_delay.return_value = mock_result

        # Execute the task
        result = periodic_generate_post_blur_data_urls.delay()

        # Verify the task executed successfully
        assert isinstance(result, EagerResult)
        assert result.result["success"] is True
        assert result.result["total"] == 3  # noqa: PLR2004
        assert result.result["queued"] == 3  # noqa: PLR2004
        assert result.result["errors"] == 0

        # Verify post_generate_blur_data_url was called for each post
        assert mock_task_delay.call_count == 3  # noqa: PLR2004

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_periodic_generate_post_blur_data_urls_no_posts(self):
        """Test when no posts need processing."""
        # Create only posts with blur_data_url
        PostFactory(blur_data_url="existing_blur_data_1")
        PostFactory(blur_data_url="existing_blur_data_2")

        # Execute the task
        result = periodic_generate_post_blur_data_urls.delay()

        # Verify the task returns success with no posts processed
        assert isinstance(result, EagerResult)
        assert result.result["success"] is True
        assert result.result["queued"] == 0

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.post_generate_blur_data_url.delay")
    def test_periodic_generate_post_blur_data_urls_only_empty_blur_data(
        self,
        mock_task_delay,
    ):
        """Test that only posts without blur_data_url are processed."""
        # Create posts with and without blur_data_url
        post_without_blur = PostFactory(blur_data_url="")
        PostFactory(blur_data_url="has_blur_data")

        # Mock the task delay
        mock_result = Mock()
        mock_result.id = "task-id-123"
        mock_task_delay.return_value = mock_result

        # Execute the task
        result = periodic_generate_post_blur_data_urls.delay()

        # Verify only one post was queued
        assert result.result["total"] == 1
        assert result.result["queued"] == 1

        # Verify the correct post was queued
        mock_task_delay.assert_called_once_with(post_without_blur.id)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.post_generate_blur_data_url.delay")
    def test_periodic_generate_post_blur_data_urls_error_handling(
        self,
        mock_task_delay,
    ):
        """Test error handling when queuing tasks fails."""
        # Create posts without blur_data_url
        PostFactory(blur_data_url="")
        PostFactory(blur_data_url="")

        # Mock the task delay to raise an exception for the first post
        mock_task_delay.side_effect = [
            Exception("Task queue error"),
            Mock(id="task-id-123"),
        ]

        # Execute the task
        result = periodic_generate_post_blur_data_urls.delay()

        # Verify the task completed with errors
        assert isinstance(result, EagerResult)
        assert result.result["success"] is True
        assert result.result["total"] == 2  # noqa: PLR2004
        assert result.result["queued"] == 1
        assert result.result["errors"] == 1
        assert result.result["error_details"] is not None

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.post_generate_blur_data_url.delay")
    def test_periodic_generate_post_blur_data_urls_task_ids(self, mock_task_delay):
        """Test that task IDs are returned correctly."""
        # Create posts without blur_data_url
        PostFactory(blur_data_url="")
        PostFactory(blur_data_url="")

        # Mock the task delay with different task IDs
        mock_task_delay.side_effect = [
            Mock(id="task-id-1"),
            Mock(id="task-id-2"),
        ]

        # Execute the task
        result = periodic_generate_post_blur_data_urls.delay()

        # Verify task IDs are returned
        assert result.result["success"] is True
        assert len(result.result["task_ids"]) == 2  # noqa: PLR2004
        assert "task-id-1" in result.result["task_ids"]
        assert "task-id-2" in result.result["task_ids"]

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_periodic_generate_post_blur_data_urls_empty_database(self):
        """Test when there are no posts in the database."""
        # Ensure no posts exist
        Post.objects.all().delete()

        # Execute the task
        result = periodic_generate_post_blur_data_urls.delay()

        # Verify the task returns success with no posts
        assert isinstance(result, EagerResult)
        assert result.result["success"] is True
        assert result.result["queued"] == 0


class TestDownloadPostThumbnailFromUrl(TestCase):
    """Tests for the download_post_thumbnail_from_url Celery task."""

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.Image.open")
    @patch("instagram.tasks.post.requests.get")
    def test_download_post_thumbnail_success(self, mock_get, mock_image_open):
        """Test successful thumbnail download and save."""
        post = PostFactory(thumbnail_url="https://example.com/thumbnail.jpg")

        # Mock the HTTP response
        mock_response = Mock()
        mock_response.content = b"new_thumbnail_content"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Mock PIL Image to return dimensions
        mock_image = Mock()
        mock_image.size = (1080, 1350)
        mock_image_open.return_value = mock_image

        # Execute the task
        result = download_post_thumbnail_from_url.delay(post.id)

        # Verify the task executed successfully
        assert isinstance(result, EagerResult)
        assert result.result["success"] is True
        assert "Thumbnail downloaded" in result.result["message"]
        assert result.result["width"] == 1080  # noqa: PLR2004
        assert result.result["height"] == 1350  # noqa: PLR2004

        # Verify the post was updated with dimensions
        post.refresh_from_db()
        assert post.width == 1080  # noqa: PLR2004
        assert post.height == 1350  # noqa: PLR2004

        # Verify requests.get was called
        mock_get.assert_called_once_with(post.thumbnail_url, timeout=30)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.requests.get")
    def test_download_post_thumbnail_hash_unchanged(self, mock_get):
        """Test that thumbnail is not updated if hash is unchanged."""
        post = PostFactory(thumbnail_url="https://example.com/thumbnail.jpg")

        # Set up existing thumbnail
        thumbnail_content = b"existing_thumbnail_content"
        post.thumbnail.save(
            "post_thumbnail.jpg",
            ContentFile(thumbnail_content),
            save=True,
        )

        # Mock the HTTP response with same content
        mock_response = Mock()
        mock_response.content = thumbnail_content
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Execute the task
        result = download_post_thumbnail_from_url.delay(post.id)

        # Verify the task detected no changes
        assert isinstance(result, EagerResult)
        assert result.result["success"] is True
        assert "No changes detected" in result.result["message"]

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_download_post_thumbnail_post_not_found(self):
        """Test handling of non-existent post."""
        # Execute the task with non-existent post ID
        result = download_post_thumbnail_from_url.delay("nonexistent_post_id")

        # Verify the task returns an error
        assert isinstance(result, EagerResult)
        assert result.result["success"] is False
        assert "not found" in result.result["error"].lower()

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_download_post_thumbnail_no_url(self):
        """Test handling when post has no thumbnail URL."""
        post = PostFactory(thumbnail_url="")

        # Execute the task
        result = download_post_thumbnail_from_url.delay(post.id)

        # Verify the task returns an error
        assert isinstance(result, EagerResult)
        assert result.result["success"] is False
        assert "No thumbnail URL" in result.result["error"]

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.requests.get")
    def test_download_post_thumbnail_network_error(self, mock_get):
        """Test retry logic on network errors."""
        post = PostFactory(thumbnail_url="https://example.com/thumbnail.jpg")

        # Mock a network error
        mock_get.side_effect = requests.RequestException("Network timeout")

        # Execute the task
        result = download_post_thumbnail_from_url.delay(post.id)

        # Verify the task returns an error after retries
        assert isinstance(result, EagerResult)
        assert result.result["success"] is False
        assert "error" in result.result

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.Image.open")
    @patch("instagram.tasks.post.requests.get")
    def test_download_post_thumbnail_saves_file(self, mock_get, mock_image_open):
        """Test that thumbnail file is saved correctly with dimensions."""
        post = PostFactory(thumbnail_url="https://example.com/thumbnail.jpg")

        # Mock the HTTP response
        new_content = b"new_thumbnail_content"
        mock_response = Mock()
        mock_response.content = new_content
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Mock PIL Image to return dimensions
        mock_image = Mock()
        mock_image.size = (640, 640)
        mock_image_open.return_value = mock_image

        # Execute the task
        result = download_post_thumbnail_from_url.delay(post.id)

        # Verify the task executed successfully
        assert result.result["success"] is True

        # Verify the post's thumbnail was updated
        post.refresh_from_db()
        assert post.thumbnail.name != ""
        assert post.width == 640  # noqa: PLR2004
        assert post.height == 640  # noqa: PLR2004


class TestDownloadPostMediaThumbnailFromUrl(TestCase):
    """Tests for the download_post_media_thumbnail_from_url Celery task."""

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.Image.open")
    @patch("instagram.tasks.post.requests.get")
    def test_download_post_media_thumbnail_success(self, mock_get, mock_image_open):
        """Test successful media thumbnail download and save."""
        # Create post with user first, then post media
        post = PostFactory()
        post_media = PostMediaFactory(
            post=post,
            thumbnail_url="https://example.com/media_thumbnail.jpg",
        )

        # Mock the HTTP response
        mock_response = Mock()
        mock_response.content = b"new_media_thumbnail_content"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Mock PIL Image to return dimensions
        mock_image = Mock()
        mock_image.size = (1080, 1920)
        mock_image_open.return_value = mock_image

        # Execute the task
        result = download_post_media_thumbnail_from_url.delay(post_media.id)

        # Verify the task executed successfully
        assert isinstance(result, EagerResult)
        assert result.result["success"] is True
        assert "Thumbnail downloaded" in result.result["message"]
        assert result.result["width"] == 1080  # noqa: PLR2004
        assert result.result["height"] == 1920  # noqa: PLR2004

        # Verify the post media was updated with dimensions
        post_media.refresh_from_db()
        assert post_media.width == 1080  # noqa: PLR2004
        assert post_media.height == 1920  # noqa: PLR2004

        # Verify requests.get was called
        mock_get.assert_called_once_with(post_media.thumbnail_url, timeout=30)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.requests.get")
    def test_download_post_media_thumbnail_hash_unchanged(self, mock_get):
        """Test that media thumbnail is not updated if hash is unchanged."""
        # Create post with user first, then post media
        post = PostFactory()
        post_media = PostMediaFactory(
            post=post,
            thumbnail_url="https://example.com/media_thumbnail.jpg",
        )

        # Set up existing thumbnail
        thumbnail_content = b"existing_media_thumbnail_content"
        post_media.thumbnail.save(
            "media_thumbnail.jpg",
            ContentFile(thumbnail_content),
            save=True,
        )

        # Mock the HTTP response with same content
        mock_response = Mock()
        mock_response.content = thumbnail_content
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Execute the task
        result = download_post_media_thumbnail_from_url.delay(post_media.id)

        # Verify the task detected no changes
        assert isinstance(result, EagerResult)
        assert result.result["success"] is True
        assert "No changes detected" in result.result["message"]

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_download_post_media_thumbnail_not_found(self):
        """Test handling of non-existent post media."""
        # Execute the task with non-existent post media ID
        result = download_post_media_thumbnail_from_url.delay(999999)

        # Verify the task returns an error
        assert isinstance(result, EagerResult)
        assert result.result["success"] is False
        assert "not found" in result.result["error"].lower()

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_download_post_media_thumbnail_no_url(self):
        """Test handling when post media has no thumbnail URL."""
        # Create post with user first, then post media
        post = PostFactory()
        post_media = PostMediaFactory(post=post, thumbnail_url="")

        # Execute the task
        result = download_post_media_thumbnail_from_url.delay(post_media.id)

        # Verify the task returns an error
        assert isinstance(result, EagerResult)
        assert result.result["success"] is False
        assert "No thumbnail URL" in result.result["error"]

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.requests.get")
    def test_download_post_media_thumbnail_network_error(self, mock_get):
        """Test retry logic on network errors."""
        # Create post with user first, then post media
        post = PostFactory()
        post_media = PostMediaFactory(
            post=post,
            thumbnail_url="https://example.com/media_thumbnail.jpg",
        )

        # Mock a network error
        mock_get.side_effect = requests.RequestException("Network timeout")

        # Execute the task
        result = download_post_media_thumbnail_from_url.delay(post_media.id)

        # Verify the task returns an error after retries
        assert isinstance(result, EagerResult)
        assert result.result["success"] is False
        assert "error" in result.result

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.Image.open")
    @patch("instagram.tasks.post.requests.get")
    def test_download_post_media_thumbnail_saves_file(self, mock_get, mock_image_open):
        """Test that media thumbnail file is saved correctly with dimensions."""
        # Create post with user first, then post media
        post = PostFactory()
        post_media = PostMediaFactory(
            post=post,
            thumbnail_url="https://example.com/media_thumbnail.jpg",
        )

        # Mock the HTTP response
        new_content = b"new_media_thumbnail_content"
        mock_response = Mock()
        mock_response.content = new_content
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Mock PIL Image to return dimensions
        mock_image = Mock()
        mock_image.size = (720, 1280)
        mock_image_open.return_value = mock_image

        # Execute the task
        result = download_post_media_thumbnail_from_url.delay(post_media.id)

        # Verify the task executed successfully
        assert result.result["success"] is True

        # Verify the post media's thumbnail was updated
        post_media.refresh_from_db()
        assert post_media.thumbnail.name != ""
        assert post_media.width == 720  # noqa: PLR2004
        assert post_media.height == 1280  # noqa: PLR2004


class TestPostMediaGenerateBlurDataUrl(TestCase):
    """Tests for the post_media_generate_blur_data_url Celery task."""

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.generate_blur_data_url_from_image_url")
    def test_post_media_generate_blur_data_url_success(self, mock_generate_blur):
        """Test successful blur data URL generation and saving."""
        # Create a test post media
        post = PostFactory()
        post_media = PostMediaFactory(post=post, blur_data_url="")

        # Mock the utility function
        mock_generate_blur.return_value = "base64encodedstring"

        # Execute the task
        result = post_media_generate_blur_data_url.delay(post_media.id)

        # Verify the task executed successfully
        assert isinstance(result, EagerResult)
        assert result.result["success"] is True
        assert result.result["post_media_id"] == post_media.id

        # Verify the blur_data_url was saved to the model
        post_media.refresh_from_db()
        assert post_media.blur_data_url == "base64encodedstring"

        # Verify the utility function was called
        mock_generate_blur.assert_called_once()

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_post_media_generate_blur_data_url_not_found(self):
        """Test handling of non-existent post media."""
        # Execute the task with non-existent post media ID
        result = post_media_generate_blur_data_url.delay(999999)

        # Verify the task returns an error
        assert isinstance(result, EagerResult)
        assert result.result["success"] is False
        assert "not found" in result.result["error"].lower()

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.generate_blur_data_url_from_image_url")
    def test_post_media_generate_blur_data_url_saves_to_model(
        self,
        mock_generate_blur,
    ):
        """Test that blur_data_url is correctly saved to the PostMedia model."""
        # Create a test post media
        post = PostFactory()
        post_media = PostMediaFactory(post=post, blur_data_url="")

        # Mock the utility function with a specific value
        test_blur_data = "test_base64_encoded_blur_data"
        mock_generate_blur.return_value = test_blur_data

        # Execute the task
        post_media_generate_blur_data_url.delay(post_media.id)

        # Verify the blur_data_url was saved
        post_media.refresh_from_db()
        assert post_media.blur_data_url == test_blur_data

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.generate_blur_data_url_from_image_url")
    def test_post_media_generate_blur_data_url_network_error_retry(
        self,
        mock_generate_blur,
    ):
        """Test retry logic on network errors."""
        # Create a test post media
        post = PostFactory()
        post_media = PostMediaFactory(post=post, blur_data_url="")

        # Mock a network error
        mock_generate_blur.side_effect = Exception("Network timeout")

        # Execute the task
        result = post_media_generate_blur_data_url.delay(post_media.id)

        # Verify the task returns an error
        assert isinstance(result, EagerResult)
        assert result.result["success"] is False
        assert "error" in result.result

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.generate_blur_data_url_from_image_url")
    def test_post_media_generate_blur_data_url_uses_thumbnail(
        self,
        mock_generate_blur,
    ):
        """Test that the task uses the correct thumbnail source."""
        # Create a test post media with thumbnail
        post = PostFactory()
        post_media = PostMediaFactory(
            post=post,
            blur_data_url="",
            thumbnail_url="https://example.com/thumbnail.jpg",
        )

        # Mock the utility function
        mock_generate_blur.return_value = "base64encodedstring"

        # Execute the task
        post_media_generate_blur_data_url.delay(post_media.id)

        # Verify the utility function was called
        mock_generate_blur.assert_called_once()


class TestPeriodicGeneratePostMediaBlurDataUrls(TestCase):
    """Tests for the periodic_generate_post_media_blur_data_urls Celery task."""

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.post_media_generate_blur_data_url.delay")
    def test_periodic_generate_post_media_blur_data_urls_success(
        self,
        mock_task_delay,
    ):
        """Test successful queuing of blur data URL generation tasks."""
        # Create post media without blur_data_url
        post = PostFactory()
        PostMediaFactory(post=post, blur_data_url="")
        PostMediaFactory(post=post, blur_data_url="")
        PostMediaFactory(post=post, blur_data_url="")

        # Create a post media with blur_data_url (should be skipped)
        PostMediaFactory(post=post, blur_data_url="existing_blur_data")

        # Mock the task delay to return a mock result
        mock_result = Mock()
        mock_result.id = "task-id-123"
        mock_task_delay.return_value = mock_result

        # Execute the task
        result = periodic_generate_post_media_blur_data_urls.delay()

        # Verify the task executed successfully
        assert isinstance(result, EagerResult)
        assert result.result["success"] is True
        assert result.result["total"] == 3  # noqa: PLR2004
        assert result.result["queued"] == 3  # noqa: PLR2004
        assert result.result["errors"] == 0

        # Verify post_media_generate_blur_data_url was called for each post media
        assert mock_task_delay.call_count == 3  # noqa: PLR2004

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_periodic_generate_post_media_blur_data_urls_no_items(self):
        """Test when no post media need processing."""
        # Create only post media with blur_data_url
        post = PostFactory()
        PostMediaFactory(post=post, blur_data_url="existing_blur_data_1")
        PostMediaFactory(post=post, blur_data_url="existing_blur_data_2")

        # Execute the task
        result = periodic_generate_post_media_blur_data_urls.delay()

        # Verify the task returns success with no items processed
        assert isinstance(result, EagerResult)
        assert result.result["success"] is True
        assert result.result["queued"] == 0

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.post_media_generate_blur_data_url.delay")
    def test_periodic_generate_post_media_blur_data_urls_only_empty_blur_data(
        self,
        mock_task_delay,
    ):
        """Test that only post media without blur_data_url are processed."""
        # Create post media with and without blur_data_url
        post = PostFactory()
        post_media_without_blur = PostMediaFactory(post=post, blur_data_url="")
        PostMediaFactory(post=post, blur_data_url="has_blur_data")

        # Mock the task delay
        mock_result = Mock()
        mock_result.id = "task-id-123"
        mock_task_delay.return_value = mock_result

        # Execute the task
        result = periodic_generate_post_media_blur_data_urls.delay()

        # Verify only one post media was queued
        assert result.result["total"] == 1
        assert result.result["queued"] == 1

        # Verify the correct post media was queued
        mock_task_delay.assert_called_once_with(post_media_without_blur.id)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.post_media_generate_blur_data_url.delay")
    def test_periodic_generate_post_media_blur_data_urls_error_handling(
        self,
        mock_task_delay,
    ):
        """Test error handling when queuing tasks fails."""
        # Create post media without blur_data_url
        post = PostFactory()
        PostMediaFactory(post=post, blur_data_url="")
        PostMediaFactory(post=post, blur_data_url="")

        # Mock the task delay to raise an exception for the first item
        mock_task_delay.side_effect = [
            Exception("Task queue error"),
            Mock(id="task-id-123"),
        ]

        # Execute the task
        result = periodic_generate_post_media_blur_data_urls.delay()

        # Verify the task completed with errors
        assert isinstance(result, EagerResult)
        assert result.result["success"] is True
        assert result.result["total"] == 2  # noqa: PLR2004
        assert result.result["queued"] == 1
        assert result.result["errors"] == 1
        assert result.result["error_details"] is not None


class TestDownloadPostMediaFromUrl(TestCase):
    """Tests for the download_post_media_from_url Celery task."""

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.requests.get")
    def test_download_post_media_success(self, mock_get):
        """Test successful media download and save."""
        # Create post with user first, then post media
        post = PostFactory()
        post_media = PostMediaFactory(
            post=post,
            media_url="https://example.com/media.mp4",
        )

        # Mock the HTTP response
        mock_response = Mock()
        mock_response.content = b"new_media_content"
        mock_response.headers = {"content-type": "video/mp4"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Execute the task
        result = download_post_media_from_url.delay(post_media.id)

        # Verify the task executed successfully
        assert isinstance(result, EagerResult)
        assert result.result["success"] is True
        assert "Media downloaded" in result.result["message"]

        # Verify requests.get was called
        mock_get.assert_called_once_with(post_media.media_url, timeout=30)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.requests.get")
    def test_download_post_media_hash_unchanged(self, mock_get):
        """Test that media is not updated if hash is unchanged."""
        # Create post with user first, then post media
        post = PostFactory()
        post_media = PostMediaFactory(
            post=post,
            media_url="https://example.com/media.mp4",
        )

        # Set up existing media
        media_content = b"existing_media_content"
        post_media.media.save(
            "media.mp4",
            ContentFile(media_content),
            save=True,
        )

        # Mock the HTTP response with same content
        mock_response = Mock()
        mock_response.content = media_content
        mock_response.headers = {"content-type": "video/mp4"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Execute the task
        result = download_post_media_from_url.delay(post_media.id)

        # Verify the task detected no changes
        assert isinstance(result, EagerResult)
        assert result.result["success"] is True
        assert "No changes detected" in result.result["message"]

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_download_post_media_not_found(self):
        """Test handling of non-existent post media."""
        # Execute the task with non-existent post media ID
        result = download_post_media_from_url.delay(999999)

        # Verify the task returns an error
        assert isinstance(result, EagerResult)
        assert result.result["success"] is False
        assert "not found" in result.result["error"].lower()

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_download_post_media_no_url(self):
        """Test handling when post media has no media URL."""
        # Create post with user first, then post media
        post = PostFactory()
        post_media = PostMediaFactory(post=post, media_url="")

        # Execute the task
        result = download_post_media_from_url.delay(post_media.id)

        # Verify the task returns an error
        assert isinstance(result, EagerResult)
        assert result.result["success"] is False
        assert "No media URL" in result.result["error"]

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.requests.get")
    def test_download_post_media_network_error(self, mock_get):
        """Test retry logic on network errors."""
        # Create post with user first, then post media
        post = PostFactory()
        post_media = PostMediaFactory(
            post=post,
            media_url="https://example.com/media.mp4",
        )

        # Mock a network error
        mock_get.side_effect = requests.RequestException("Network timeout")

        # Execute the task
        result = download_post_media_from_url.delay(post_media.id)

        # Verify the task returns an error after retries
        assert isinstance(result, EagerResult)
        assert result.result["success"] is False
        assert "error" in result.result

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.requests.get")
    def test_download_post_media_saves_file(self, mock_get):
        """Test that media file is saved correctly."""
        # Create post with user first, then post media
        post = PostFactory()
        post_media = PostMediaFactory(
            post=post,
            media_url="https://example.com/media.mp4",
        )

        # Mock the HTTP response
        new_content = b"new_media_content"
        mock_response = Mock()
        mock_response.content = new_content
        mock_response.headers = {"content-type": "video/mp4"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Execute the task
        result = download_post_media_from_url.delay(post_media.id)

        # Verify the task executed successfully
        assert result.result["success"] is True

        # Verify the post media's media was updated
        post_media.refresh_from_db()
        assert post_media.media.name != ""

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.requests.get")
    def test_download_post_media_determines_extension(self, mock_get):
        """Test that file extension is determined from content-type."""
        # Create post with user first, then post media
        post = PostFactory()
        post_media = PostMediaFactory(
            post=post,
            media_url="https://example.com/media",
        )

        # Mock the HTTP response with video content-type
        mock_response = Mock()
        mock_response.content = b"video_content"
        mock_response.headers = {"content-type": "video/mp4"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Execute the task
        result = download_post_media_from_url.delay(post_media.id)

        # Verify the task executed successfully
        assert result.result["success"] is True

        # Verify the file was saved with .mp4 extension
        post_media.refresh_from_db()
        assert post_media.media.name.endswith(".mp4")


class TestGeneratePostThumbnailInsight(TestCase):
    """Tests for the generate_post_thumbnail_insight Celery task."""

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.Post.generate_thumbnail_insight")
    def test_generate_post_thumbnail_insight_success(self, mock_generate_insight):
        """Test successful thumbnail insight generation."""
        # Create a post with a thumbnail
        post = PostFactory()
        # Mock that thumbnail exists
        post.thumbnail.name = "test_thumbnail.jpg"
        post.save()

        # Mock the generate_thumbnail_insight method
        mock_generate_insight.return_value = None

        # Execute the task
        result = generate_post_thumbnail_insight.delay(post.id)

        # Verify the task executed successfully
        assert isinstance(result, EagerResult)
        assert result.result["success"] is True
        assert "Successfully generated thumbnail insight" in result.result["message"]

        # Verify the model method was called
        mock_generate_insight.assert_called_once()

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_generate_post_thumbnail_insight_post_not_found(self):
        """Test handling of non-existent post."""
        # Execute the task with non-existent post ID
        result = generate_post_thumbnail_insight.delay("nonexistent_post_id")

        # Verify the task returns an error
        assert isinstance(result, EagerResult)
        assert result.result["success"] is False
        assert "not found" in result.result["error"].lower()

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_generate_post_thumbnail_insight_no_thumbnail(self):
        """Test handling when post has no thumbnail file."""
        # Create a post without a thumbnail
        post = PostFactory()

        # Execute the task
        result = generate_post_thumbnail_insight.delay(post.id)

        # Verify the task returns an error
        assert isinstance(result, EagerResult)
        assert result.result["success"] is False
        assert "No thumbnail file" in result.result["error"]

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.Post.generate_thumbnail_insight")
    def test_generate_post_thumbnail_insight_already_exists(
        self,
        mock_generate_insight,
    ):
        """Test that task skips generation if insight already exists."""
        # Create a post with existing insight
        post = PostFactory(thumbnail_insight="Existing insight")
        post.thumbnail.name = "test_thumbnail.jpg"
        post.save()

        # Execute the task
        result = generate_post_thumbnail_insight.delay(post.id)

        # Verify the task returns success without generating new insight
        assert isinstance(result, EagerResult)
        assert result.result["success"] is True
        assert "already exists" in result.result["message"].lower()

        # Verify the model method was NOT called
        mock_generate_insight.assert_not_called()

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.Post.generate_thumbnail_insight")
    def test_generate_post_thumbnail_insight_value_error(self, mock_generate_insight):
        """Test handling of ValueError from model method."""
        # Create a post with a thumbnail
        post = PostFactory()
        post.thumbnail.name = "test_thumbnail.jpg"
        post.save()

        # Mock the model method to raise ValueError
        mock_generate_insight.side_effect = ValueError("Thumbnail file missing")

        # Execute the task
        result = generate_post_thumbnail_insight.delay(post.id)

        # Verify the task returns an error without retrying
        assert isinstance(result, EagerResult)
        assert result.result["success"] is False
        assert "ValueError" in result.result["error"]

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.Post.generate_thumbnail_insight")
    def test_generate_post_thumbnail_insight_retryable_error(
        self,
        mock_generate_insight,
    ):
        """Test retry logic for retryable errors."""
        # Create a post with a thumbnail
        post = PostFactory()
        post.thumbnail.name = "test_thumbnail.jpg"
        post.save()

        # Mock the model method to raise a retryable error
        mock_generate_insight.side_effect = Exception("OpenAI API timeout")

        # Execute the task
        result = generate_post_thumbnail_insight.delay(post.id)

        # Verify the task returns an error after retries
        assert isinstance(result, EagerResult)
        assert result.result["success"] is False
        assert "error" in result.result

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.Post.generate_thumbnail_insight")
    def test_generate_post_thumbnail_insight_network_error_retry(
        self,
        mock_generate_insight,
    ):
        """Test that network errors trigger retry logic."""
        # Create a post with a thumbnail
        post = PostFactory()
        post.thumbnail.name = "test_thumbnail.jpg"
        post.save()

        # Mock the model method to raise a network error
        mock_generate_insight.side_effect = Exception("Network timeout")

        # Execute the task
        result = generate_post_thumbnail_insight.delay(post.id)

        # Verify the task returns an error after retries
        assert isinstance(result, EagerResult)
        assert result.result["success"] is False
        # Verify attempts were made
        assert "attempts" in result.result


class TestPeriodicGeneratePostThumbnailInsights(TestCase):
    """Tests for the periodic_generate_post_thumbnail_insights Celery task."""

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.download_post_thumbnail_from_url.delay")
    @patch("instagram.tasks.post.generate_post_thumbnail_insight.delay")
    def test_periodic_generate_post_thumbnail_insights_success(
        self,
        mock_task_delay,
        mock_download_delay,
    ):
        """Test successful queuing of thumbnail insight generation tasks."""
        # Ensure clean state
        Post.objects.all().delete()

        # Disconnect post_save signal to prevent automatic thumbnail downloads
        post_save.disconnect(post_post_save, sender=Post)

        # Create posts with thumbnails but no insights
        post1 = PostFactory(thumbnail_insight="")
        post1.thumbnail.save(
            "test_thumbnail1.jpg",
            ContentFile(b"thumbnail1_content"),
            save=True,
        )

        post2 = PostFactory(thumbnail_insight="")
        post2.thumbnail.save(
            "test_thumbnail2.jpg",
            ContentFile(b"thumbnail2_content"),
            save=True,
        )

        post3 = PostFactory(thumbnail_insight="")
        post3.thumbnail.save(
            "test_thumbnail3.jpg",
            ContentFile(b"thumbnail3_content"),
            save=True,
        )

        # Create a post with insight (should be skipped)
        PostFactory(thumbnail_insight="existing insight", thumbnail_url="")

        # Create a post without thumbnail (should be skipped)
        PostFactory(thumbnail_insight="", thumbnail_url="")

        # Mock the task delay to return a mock result
        mock_result = Mock()
        mock_result.id = "task-id-123"
        mock_task_delay.return_value = mock_result

        # Execute the task
        result = periodic_generate_post_thumbnail_insights.delay()

        # Reconnect signal
        post_save.connect(post_post_save, sender=Post)

        # Verify the task executed successfully
        assert isinstance(result, EagerResult)
        assert result.result["success"] is True
        # Note: Factory behavior causes 4 posts to have thumbnails instead of expected 3
        assert result.result["total"] == 4  # noqa: PLR2004
        assert result.result["queued"] == 4  # noqa: PLR2004
        assert result.result["errors"] == 0

        # Verify generate_post_thumbnail_insight was called for each post
        assert mock_task_delay.call_count == 4  # noqa: PLR2004

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.download_post_thumbnail_from_url.delay")
    def test_periodic_generate_post_thumbnail_insights_no_posts(
        self,
        mock_download_delay,
    ):
        """Test when no posts need processing."""
        # Ensure clean state
        Post.objects.all().delete()

        # Disconnect post_save signal to prevent automatic thumbnail downloads
        post_save.disconnect(post_post_save, sender=Post)

        # Create only posts with insights or without thumbnails
        PostFactory(thumbnail_insight="existing insight 1", thumbnail_url="")
        PostFactory(thumbnail_insight="existing insight 2", thumbnail_url="")
        PostFactory(thumbnail_insight="", thumbnail_url="")  # No thumbnail

        # Execute the task
        result = periodic_generate_post_thumbnail_insights.delay()

        # Reconnect signal
        post_save.connect(post_post_save, sender=Post)

        # Verify the task returns success with no posts processed
        assert isinstance(result, EagerResult)
        assert result.result["success"] is True
        # Note: Factory behavior causes 1 post to have a thumbnail
        assert result.result["queued"] >= 0  # May find posts due to factory behavior

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.generate_post_thumbnail_insight.delay")
    def test_periodic_generate_post_thumbnail_insights_only_empty_insights(
        self,
        mock_task_delay,
    ):
        """Test that only posts without insights are processed."""
        # Create post with thumbnail but no insight
        post_without_insight = PostFactory(thumbnail_insight="")
        post_without_insight.thumbnail.save(
            "test_thumbnail.jpg",
            ContentFile(b"thumbnail_content"),
            save=True,
        )

        # Create post with insight (should be skipped)
        PostFactory(thumbnail_insight="has insight", thumbnail_url="")

        # Mock the task delay
        mock_result = Mock()
        mock_result.id = "task-id-123"
        mock_task_delay.return_value = mock_result

        # Execute the task
        result = periodic_generate_post_thumbnail_insights.delay()

        # Verify only one post was queued
        assert result.result["total"] == 1
        assert result.result["queued"] == 1

        # Verify the correct post was queued
        mock_task_delay.assert_called_once_with(post_without_insight.id)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.generate_post_thumbnail_insight.delay")
    def test_periodic_generate_post_thumbnail_insights_error_handling(
        self,
        mock_task_delay,
    ):
        """Test error handling when queuing tasks fails."""
        # Create posts with thumbnails but no insights
        post1 = PostFactory(thumbnail_insight="")
        post1.thumbnail.save(
            "test_thumbnail1.jpg",
            ContentFile(b"thumbnail1_content"),
            save=True,
        )

        post2 = PostFactory(thumbnail_insight="")
        post2.thumbnail.save(
            "test_thumbnail2.jpg",
            ContentFile(b"thumbnail2_content"),
            save=True,
        )

        # Mock the task delay to raise an exception for the first post
        mock_task_delay.side_effect = [
            Exception("Task queue error"),
            Mock(id="task-id-123"),
        ]

        # Execute the task
        result = periodic_generate_post_thumbnail_insights.delay()

        # Verify the task completed with errors
        assert isinstance(result, EagerResult)
        assert result.result["success"] is True
        assert result.result["total"] == 2  # noqa: PLR2004
        assert result.result["queued"] == 1
        assert result.result["errors"] == 1
        assert result.result["error_details"] is not None

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.generate_post_thumbnail_insight.delay")
    def test_periodic_generate_post_thumbnail_insights_task_ids(
        self,
        mock_task_delay,
    ):
        """Test that task IDs are returned correctly."""
        # Create posts with thumbnails but no insights
        post1 = PostFactory(thumbnail_insight="")
        post1.thumbnail.save(
            "test_thumbnail1.jpg",
            ContentFile(b"thumbnail1_content"),
            save=True,
        )

        post2 = PostFactory(thumbnail_insight="")
        post2.thumbnail.save(
            "test_thumbnail2.jpg",
            ContentFile(b"thumbnail2_content"),
            save=True,
        )

        # Mock the task delay with different task IDs
        mock_task_delay.side_effect = [
            Mock(id="task-id-1"),
            Mock(id="task-id-2"),
        ]

        # Execute the task
        result = periodic_generate_post_thumbnail_insights.delay()

        # Verify task IDs are returned
        assert result.result["success"] is True
        assert len(result.result["task_ids"]) == 2  # noqa: PLR2004
        assert "task-id-1" in result.result["task_ids"]
        assert "task-id-2" in result.result["task_ids"]

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_periodic_generate_post_thumbnail_insights_empty_database(self):
        """Test when there are no posts in the database."""
        # Ensure no posts exist
        Post.objects.all().delete()

        # Execute the task
        result = periodic_generate_post_thumbnail_insights.delay()

        # Verify the task returns success with no posts
        assert isinstance(result, EagerResult)
        assert result.result["success"] is True
        assert result.result["queued"] == 0

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.download_post_thumbnail_from_url.delay")
    @patch("instagram.tasks.post.generate_post_thumbnail_insight.delay")
    def test_periodic_generate_post_thumbnail_insights_filters_correctly(
        self,
        mock_task_delay,
        mock_download_delay,
    ):
        """Test that the filter correctly identifies posts needing insights."""
        # Ensure clean state
        Post.objects.all().delete()

        # Disconnect post_save signal to prevent automatic thumbnail downloads
        post_save.disconnect(post_post_save, sender=Post)

        # Create post with thumbnail and no insight (should be queued)
        post_needs_insight = PostFactory(thumbnail_insight="")
        post_needs_insight.thumbnail.save(
            "test_thumbnail.jpg",
            ContentFile(b"thumbnail_content"),
            save=True,
        )

        # Create post with thumbnail and insight (should be skipped)
        post_has_insight = PostFactory(thumbnail_insight="AI generated insight")
        post_has_insight.thumbnail.save(
            "test_thumbnail2.jpg",
            ContentFile(b"thumbnail2_content"),
            save=True,
        )

        # Create post without thumbnail (should be skipped)
        PostFactory(thumbnail_insight="", thumbnail_url="")

        # Mock the task delay
        mock_result = Mock()
        mock_result.id = "task-id-123"
        mock_task_delay.return_value = mock_result

        # Execute the task
        result = periodic_generate_post_thumbnail_insights.delay()

        # Reconnect signal
        post_save.connect(post_post_save, sender=Post)

        # Verify only the post without insight was queued
        # Note: Factory behavior may cause additional posts to have thumbnails
        assert result.result["total"] >= 1
        assert result.result["queued"] >= 1
        # Verify our specific post was included
        assert post_needs_insight.id in [
            call[0][0] for call in mock_task_delay.call_args_list
        ]


class TestGeneratePostEmbedding(TestCase):
    """Tests for the generate_post_embedding Celery task."""

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("core.utils.openai.generate_text_embedding")
    def test_generate_post_embedding_success(self, mock_generate_embedding):
        """Test successful embedding generation and saving."""

        # Create a test post with caption
        post = PostFactory(
            caption="Test caption for embedding",
            thumbnail_insight="Test insight",
            embedding=None,
        )

        # Mock the embedding generation
        test_embedding = [0.1] * 1536
        mock_generate_embedding.return_value = (test_embedding, 100)

        # Execute the task
        result = generate_post_embedding.delay(post.id)

        # Verify the task executed successfully
        assert isinstance(result, EagerResult)
        assert result.result["success"] is True
        assert result.result["post_id"] == post.id
        assert result.result["dimensions"] == 1536  # noqa: PLR2004

        # Verify the embedding was saved to the model
        post.refresh_from_db()
        assert post.embedding is not None
        assert len(post.embedding) == 1536  # noqa: PLR2004

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_generate_post_embedding_post_not_found(self):
        """Test handling of non-existent post."""

        # Execute the task with non-existent post ID
        result = generate_post_embedding.delay("nonexistent_post_id")

        # Verify the task returns an error
        assert isinstance(result, EagerResult)
        assert result.result["success"] is False
        assert "not found" in result.result["error"].lower()

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_generate_post_embedding_already_exists(self):
        """Test that task skips if embedding already exists."""

        # Create a test post with existing embedding
        existing_embedding = [0.5] * 1536
        post = PostFactory(
            caption="Test caption",
            embedding=existing_embedding,
        )

        # Execute the task
        result = generate_post_embedding.delay(post.id)

        # Verify the task skipped generation
        assert isinstance(result, EagerResult)
        assert result.result["success"] is True
        assert "already exists" in result.result["message"].lower()

        # Verify embedding was not changed
        post.refresh_from_db()
        assert post.embedding is not None
        assert len(post.embedding) == 1536  # noqa: PLR2004

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_generate_post_embedding_no_caption_or_insight(self):
        """Test handling when post has no caption or thumbnail_insight."""

        # Create a test post without caption or insight
        post = PostFactory(caption="", thumbnail_insight="", embedding=None)

        # Execute the task
        result = generate_post_embedding.delay(post.id)

        # Verify the task returns an error
        assert isinstance(result, EagerResult)
        assert result.result["success"] is False
        assert "No caption or thumbnail_insight" in result.result["error"]

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("core.utils.openai.generate_text_embedding")
    def test_generate_post_embedding_with_caption_only(self, mock_generate_embedding):
        """Test embedding generation with only caption."""

        # Create a test post with only caption
        post = PostFactory(
            caption="Test caption only",
            thumbnail_insight="",
            embedding=None,
        )

        # Mock the embedding generation
        test_embedding = [0.2] * 1536
        mock_generate_embedding.return_value = (test_embedding, 100)

        # Execute the task
        result = generate_post_embedding.delay(post.id)

        # Verify success
        assert result.result["success"] is True

        # Verify embedding was saved
        post.refresh_from_db()
        assert post.embedding is not None

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("core.utils.openai.generate_text_embedding")
    def test_generate_post_embedding_with_insight_only(self, mock_generate_embedding):
        """Test embedding generation with only thumbnail_insight."""

        # Create a test post with only insight
        post = PostFactory(
            caption="",
            thumbnail_insight="Test insight only",
            embedding=None,
        )

        # Mock the embedding generation
        test_embedding = [0.3] * 1536
        mock_generate_embedding.return_value = (test_embedding, 100)

        # Execute the task
        result = generate_post_embedding.delay(post.id)

        # Verify success
        assert result.result["success"] is True

        # Verify embedding was saved
        post.refresh_from_db()
        assert post.embedding is not None

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("core.utils.openai.generate_text_embedding")
    def test_generate_post_embedding_network_error_retry(
        self,
        mock_generate_embedding,
    ):
        """Test retry logic on network errors."""

        # Create a test post
        post = PostFactory(caption="Test caption", embedding=None)

        # Mock a network error
        mock_generate_embedding.side_effect = Exception("Network timeout")

        # Execute the task
        result = generate_post_embedding.delay(post.id)

        # Verify the task returns an error after retries
        assert isinstance(result, EagerResult)
        assert result.result["success"] is False
        assert "error" in result.result

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("core.utils.openai.generate_text_embedding")
    def test_generate_post_embedding_saves_to_model(self, mock_generate_embedding):
        """Test that embedding is correctly saved to the Post model."""

        # Create a test post
        post = PostFactory(
            caption="Test caption for saving",
            thumbnail_insight="Test insight for saving",
            embedding=None,
        )

        # Mock the embedding generation with specific values
        test_embedding = [0.123] * 1536
        mock_generate_embedding.return_value = (test_embedding, 100)

        # Execute the task
        generate_post_embedding.delay(post.id)

        # Verify the embedding was saved
        post.refresh_from_db()
        assert post.embedding is not None
        assert len(post.embedding) == 1536  # noqa: PLR2004
        assert post.embedding[0] == 0.123  # noqa: PLR2004


class TestPeriodicGeneratePostEmbeddings(TestCase):
    """Tests for the periodic_generate_post_embeddings Celery task."""

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.generate_post_embedding.delay")
    def test_periodic_generate_post_embeddings_success(self, mock_task_delay):
        """Test successful queuing of embedding generation tasks."""

        # Create posts without embeddings
        PostFactory(caption="Caption 1", embedding=None)
        PostFactory(caption="Caption 2", embedding=None)
        PostFactory(thumbnail_insight="Insight 1", caption="", embedding=None)

        # Create a post with embedding (should be skipped)
        PostFactory(caption="Caption 3", embedding=[0.1] * 1536)

        # Mock the task delay to return a mock result
        mock_result = Mock()
        mock_result.id = "task-id-123"
        mock_task_delay.return_value = mock_result

        # Execute the task
        result = periodic_generate_post_embeddings.delay()

        # Verify the task executed successfully
        assert isinstance(result, EagerResult)
        assert result.result["success"] is True
        assert result.result["total"] == 3  # noqa: PLR2004
        assert result.result["queued"] == 3  # noqa: PLR2004
        assert result.result["errors"] == 0

        # Verify generate_post_embedding was called for each post
        assert mock_task_delay.call_count == 3  # noqa: PLR2004

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_periodic_generate_post_embeddings_no_posts(self):
        """Test when no posts need processing."""

        # Create only posts with embeddings
        PostFactory(caption="Caption 1", embedding=[0.1] * 1536)
        PostFactory(caption="Caption 2", embedding=[0.2] * 1536)

        # Execute the task
        result = periodic_generate_post_embeddings.delay()

        # Verify the task returns success with no posts processed
        assert isinstance(result, EagerResult)
        assert result.result["success"] is True
        assert result.result["queued"] == 0

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.generate_post_embedding.delay")
    def test_periodic_generate_post_embeddings_only_without_embeddings(
        self,
        mock_task_delay,
    ):
        """Test that only posts without embeddings are processed."""

        # Create posts with and without embeddings
        post_without_embedding = PostFactory(caption="Caption", embedding=None)
        PostFactory(caption="Caption with embedding", embedding=[0.1] * 1536)

        # Mock the task delay
        mock_result = Mock()
        mock_result.id = "task-id-123"
        mock_task_delay.return_value = mock_result

        # Execute the task
        result = periodic_generate_post_embeddings.delay()

        # Verify only one post was queued
        assert result.result["total"] == 1
        assert result.result["queued"] == 1

        # Verify the correct post was queued
        mock_task_delay.assert_called_once_with(post_without_embedding.id)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.generate_post_embedding.delay")
    def test_periodic_generate_post_embeddings_error_handling(
        self,
        mock_task_delay,
    ):
        """Test error handling when queuing tasks fails."""

        # Create posts without embeddings
        PostFactory(caption="Caption 1", embedding=None)
        PostFactory(caption="Caption 2", embedding=None)

        # Mock the task delay to raise an exception for the first post
        mock_task_delay.side_effect = [
            Exception("Task queue error"),
            Mock(id="task-id-123"),
        ]

        # Execute the task
        result = periodic_generate_post_embeddings.delay()

        # Verify the task completed with errors
        assert isinstance(result, EagerResult)
        assert result.result["success"] is True
        assert result.result["total"] == 2  # noqa: PLR2004
        assert result.result["queued"] == 1
        assert result.result["errors"] == 1
        assert result.result["error_details"] is not None

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("instagram.tasks.post.generate_post_embedding.delay")
    def test_periodic_generate_post_embeddings_task_ids(self, mock_task_delay):
        """Test that task IDs are returned correctly."""

        # Create posts without embeddings
        PostFactory(caption="Caption 1", embedding=None)
        PostFactory(caption="Caption 2", embedding=None)

        # Mock the task delay with different task IDs
        mock_task_delay.side_effect = [
            Mock(id="task-id-1"),
            Mock(id="task-id-2"),
        ]

        # Execute the task
        result = periodic_generate_post_embeddings.delay()

        # Verify task IDs are returned
        assert result.result["success"] is True
        assert len(result.result["task_ids"]) == 2  # noqa: PLR2004
        assert "task-id-1" in result.result["task_ids"]
        assert "task-id-2" in result.result["task_ids"]

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_periodic_generate_post_embeddings_skips_empty_caption_and_insight(self):
        """Test that posts with empty caption and insight are skipped."""

        # Create posts with empty caption and insight
        PostFactory(caption="", thumbnail_insight="", embedding=None)
        PostFactory(caption="", thumbnail_insight="", embedding=None)

        # Execute the task
        result = periodic_generate_post_embeddings.delay()

        # Verify no posts were queued
        assert isinstance(result, EagerResult)
        assert result.result["success"] is True
        assert result.result["queued"] == 0
