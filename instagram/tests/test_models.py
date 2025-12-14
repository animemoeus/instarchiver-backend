from unittest.mock import Mock
from unittest.mock import patch

import pytest

from instagram.tests.factories import StoryFactory

pytestmark = pytest.mark.django_db


class TestStoryModel:
    """Tests for the Story model methods."""

    @patch("instagram.models.story_generate_blur_data_url.delay")
    def test_generate_blur_data_url_task_queues_task(self, mock_task_delay):
        """Test that generate_blur_data_url_task queues a Celery task."""
        # Create a test story
        story = StoryFactory()

        # Mock the task delay
        mock_result = Mock()
        mock_result.id = "task-id-123"
        mock_task_delay.return_value = mock_result

        # Call the method
        story.generate_blur_data_url_task()

        # Verify the task was queued
        mock_task_delay.assert_called_once()

    @patch("instagram.models.story_generate_blur_data_url.delay")
    def test_generate_blur_data_url_task_passes_story_id(
        self,
        mock_task_delay,
    ):
        """Test that generate_blur_data_url_task passes correct story_id."""
        # Create a test story
        story = StoryFactory()

        # Mock the task delay
        mock_result = Mock()
        mock_result.id = "task-id-123"
        mock_task_delay.return_value = mock_result

        # Call the method
        story.generate_blur_data_url_task()

        # Verify the task was called with the correct story_id
        mock_task_delay.assert_called_once_with(story.story_id)

    @patch("instagram.models.story_generate_blur_data_url.delay")
    def test_generate_blur_data_url_task_multiple_calls(
        self,
        mock_task_delay,
    ):
        """Test multiple calls queue separate tasks."""
        # Create test stories
        story1 = StoryFactory()
        story2 = StoryFactory()

        # Mock the task delay
        mock_result = Mock()
        mock_result.id = "task-id-123"
        mock_task_delay.return_value = mock_result

        # Call the method on both stories
        story1.generate_blur_data_url_task()
        story2.generate_blur_data_url_task()

        # Verify the task was queued twice with different story_ids
        assert mock_task_delay.call_count == 2  # noqa: PLR2004
        mock_task_delay.assert_any_call(story1.story_id)
        mock_task_delay.assert_any_call(story2.story_id)
