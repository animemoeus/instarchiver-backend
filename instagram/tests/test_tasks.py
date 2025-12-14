from unittest.mock import Mock
from unittest.mock import patch

import pytest
from celery.result import EagerResult

from instagram.models import Story
from instagram.tasks import auto_generate_story_blur_data_urls
from instagram.tasks import story_generate_blur_data_url
from instagram.tests.factories import StoryFactory

pytestmark = pytest.mark.django_db


class TestStoryGenerateBlurDataUrl:
    """Tests for the story_generate_blur_data_url Celery task."""

    @patch("instagram.tasks.generate_blur_data_url_from_image_url")
    def test_story_generate_blur_data_url_success(
        self,
        mock_generate_blur,
        settings,
    ):
        """Test successful blur data URL generation and saving."""
        # Create a test story
        story = StoryFactory(blur_data_url="")

        # Mock the utility function
        mock_generate_blur.return_value = "base64encodedstring"

        # Enable eager execution
        settings.CELERY_TASK_ALWAYS_EAGER = True

        # Execute the task
        result = story_generate_blur_data_url.delay(story.story_id)

        # Verify the task executed successfully
        assert isinstance(result, EagerResult)
        assert result.result["success"] is True
        assert result.result["story_id"] == story.story_id

        # Verify the blur_data_url was saved to the model
        story.refresh_from_db()
        assert story.blur_data_url == "base64encodedstring"

        # Verify the utility function was called with correct URL
        mock_generate_blur.assert_called_once()

    def test_story_generate_blur_data_url_story_not_found(self, settings):
        """Test handling of non-existent story."""
        # Enable eager execution
        settings.CELERY_TASK_ALWAYS_EAGER = True

        # Execute the task with non-existent story ID
        result = story_generate_blur_data_url.delay("nonexistent_story_id")

        # Verify the task returns an error
        assert isinstance(result, EagerResult)
        assert result.result["success"] is False
        assert "not found" in result.result["error"].lower()

    @patch("instagram.tasks.generate_blur_data_url_from_image_url")
    def test_story_generate_blur_data_url_saves_to_model(
        self,
        mock_generate_blur,
        settings,
    ):
        """Test that blur_data_url is correctly saved to the Story model."""
        # Create a test story
        story = StoryFactory(blur_data_url="")

        # Mock the utility function with a specific value
        test_blur_data = "test_base64_encoded_blur_data"
        mock_generate_blur.return_value = test_blur_data

        # Enable eager execution
        settings.CELERY_TASK_ALWAYS_EAGER = True

        # Execute the task
        story_generate_blur_data_url.delay(story.story_id)

        # Verify the blur_data_url was saved
        story.refresh_from_db()
        assert story.blur_data_url == test_blur_data

    @patch("instagram.tasks.generate_blur_data_url_from_image_url")
    def test_story_generate_blur_data_url_network_error_retry(
        self,
        mock_generate_blur,
        settings,
    ):
        """Test retry logic on network errors."""
        # Create a test story
        story = StoryFactory(blur_data_url="")

        # Mock a network error
        mock_generate_blur.side_effect = Exception("Network timeout")

        # Enable eager execution
        settings.CELERY_TASK_ALWAYS_EAGER = True

        # Execute the task
        result = story_generate_blur_data_url.delay(story.story_id)

        # Verify the task returns an error
        assert isinstance(result, EagerResult)
        assert result.result["success"] is False
        assert "error" in result.result


class TestAutoGenerateStoryBlurDataUrls:
    """Tests for the auto_generate_story_blur_data_urls Celery task."""

    @patch("instagram.tasks.story_generate_blur_data_url.delay")
    def test_auto_generate_story_blur_data_urls_success(
        self,
        mock_task_delay,
        settings,
    ):
        """Test successful queuing of blur data URL generation tasks."""
        # Create stories without blur_data_url
        StoryFactory(blur_data_url="")
        StoryFactory(blur_data_url="")
        StoryFactory(blur_data_url="")

        # Create a story with blur_data_url (should be skipped)
        StoryFactory(blur_data_url="existing_blur_data")

        # Mock the task delay to return a mock result
        mock_result = Mock()
        mock_result.id = "task-id-123"
        mock_task_delay.return_value = mock_result

        # Enable eager execution
        settings.CELERY_TASK_ALWAYS_EAGER = True

        # Execute the task
        result = auto_generate_story_blur_data_urls.delay()

        # Verify the task executed successfully
        assert isinstance(result, EagerResult)
        assert result.result["success"] is True
        assert result.result["total"] == 3  # noqa: PLR2004
        assert result.result["queued"] == 3  # noqa: PLR2004
        assert result.result["errors"] == 0

        # Verify story_generate_blur_data_url was called for each story
        assert mock_task_delay.call_count == 3  # noqa: PLR2004

    def test_auto_generate_story_blur_data_urls_no_stories(self, settings):
        """Test when no stories need processing."""
        # Create only stories with blur_data_url
        StoryFactory(blur_data_url="existing_blur_data_1")
        StoryFactory(blur_data_url="existing_blur_data_2")

        # Enable eager execution
        settings.CELERY_TASK_ALWAYS_EAGER = True

        # Execute the task
        result = auto_generate_story_blur_data_urls.delay()

        # Verify the task returns success with no stories processed
        assert isinstance(result, EagerResult)
        assert result.result["success"] is True
        assert result.result["queued"] == 0

    @patch("instagram.tasks.story_generate_blur_data_url.delay")
    def test_auto_generate_story_blur_data_urls_only_empty_blur_data(
        self,
        mock_task_delay,
        settings,
    ):
        """Test that only stories without blur_data_url are processed."""
        # Create stories with and without blur_data_url
        story_without_blur = StoryFactory(blur_data_url="")
        StoryFactory(blur_data_url="has_blur_data")

        # Mock the task delay
        mock_result = Mock()
        mock_result.id = "task-id-123"
        mock_task_delay.return_value = mock_result

        # Enable eager execution
        settings.CELERY_TASK_ALWAYS_EAGER = True

        # Execute the task
        result = auto_generate_story_blur_data_urls.delay()

        # Verify only one story was queued
        assert result.result["total"] == 1
        assert result.result["queued"] == 1

        # Verify the correct story was queued
        mock_task_delay.assert_called_once_with(story_without_blur.story_id)

    @patch("instagram.tasks.story_generate_blur_data_url.delay")
    def test_auto_generate_story_blur_data_urls_error_handling(
        self,
        mock_task_delay,
        settings,
    ):
        """Test error handling when queuing tasks fails."""
        # Create stories without blur_data_url
        StoryFactory(blur_data_url="")
        StoryFactory(blur_data_url="")

        # Mock the task delay to raise an exception for the first story
        mock_task_delay.side_effect = [
            Exception("Task queue error"),
            Mock(id="task-id-123"),
        ]

        # Enable eager execution
        settings.CELERY_TASK_ALWAYS_EAGER = True

        # Execute the task
        result = auto_generate_story_blur_data_urls.delay()

        # Verify the task completed with errors
        assert isinstance(result, EagerResult)
        assert result.result["success"] is True
        assert result.result["total"] == 2  # noqa: PLR2004
        assert result.result["queued"] == 1
        assert result.result["errors"] == 1
        assert result.result["error_details"] is not None
        assert len(result.result["error_details"]) == 1

    def test_auto_generate_story_blur_data_urls_empty_database(self, settings):
        """Test when there are no stories in the database."""
        # Ensure no stories exist
        Story.objects.all().delete()

        # Enable eager execution
        settings.CELERY_TASK_ALWAYS_EAGER = True

        # Execute the task
        result = auto_generate_story_blur_data_urls.delay()

        # Verify the task returns success with no stories
        assert isinstance(result, EagerResult)
        assert result.result["success"] is True
        assert result.result["queued"] == 0
