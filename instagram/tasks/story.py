import logging

from celery import shared_task

from instagram.models import Story
from instagram.utils import generate_blur_data_url_from_image_url

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def story_generate_blur_data_url(self, story_id: str) -> dict:
    """
    Generate blur data URL for a story in the background.
    Delegates business logic to the utility function.

    Args:
        story_id (str): ID of the story to generate blur data URL for

    Returns:
        dict: Operation result with success status and details
    """
    try:
        story = Story.objects.get(story_id=story_id)
    except Story.DoesNotExist:
        logger.exception("Story with ID %s not found", story_id)
        return {"success": False, "error": "Story not found"}

    try:
        # Generate blur data URL using utility function
        # Use thumbnail.url if thumbnail exists, otherwise use thumbnail_url
        image_url = story.thumbnail.url if story.thumbnail else story.thumbnail_url
        blur_data_url = generate_blur_data_url_from_image_url(image_url)

        # Save to the model
        story.blur_data_url = blur_data_url
        story.save()

        logger.info(
            "Successfully generated blur data URL for story %s",
            story_id,
        )

        return {  # noqa: TRY300
            "success": True,
            "message": "Successfully generated blur data URL",
            "story_id": story_id,
        }

    except Exception as e:
        error_msg = str(e)

        # Determine if this is a retryable error
        retryable_keywords = [
            "network",
            "timeout",
            "connection",
            "502",
            "503",
            "504",
            "temporary",
            "rate limit",
            "api error",
        ]
        is_retryable = any(
            keyword in error_msg.lower() for keyword in retryable_keywords
        )

        if is_retryable and self.request.retries < self.max_retries:
            logger.warning(
                "Retryable error generating blur data URL for story %s "
                "(attempt %s/%s): %s",
                story_id,
                self.request.retries + 1,
                self.max_retries + 1,
                error_msg,
            )
            # Exponential backoff
            countdown = 60 * (2**self.request.retries)
            raise self.retry(exc=e, countdown=countdown) from e

        # Non-retryable error or max retries exceeded
        logger.exception(
            "Failed to generate blur data URL for story %s after %s attempts",
            story_id,
            self.request.retries + 1,
        )

        return {
            "success": False,
            "error": error_msg,
            "story_id": story_id,
            "attempts": self.request.retries + 1,
        }


@shared_task
def auto_generate_story_blur_data_urls():
    """
    Automatically generate blur data URLs for stories that don't have them yet.
    This task is designed to be run periodically via Celery Beat.

    Returns:
        dict: Summary of operations performed
    """
    try:
        # Get all stories without blur_data_url
        stories = Story.objects.filter(blur_data_url="")
        total_stories = stories.count()

        if total_stories == 0:
            logger.info("No stories found without blur data URL")
            return {
                "success": True,
                "message": "No stories to process",
                "queued": 0,
                "errors": 0,
            }

        logger.info(
            "Starting blur data URL generation for %d stories",
            total_stories,
        )

        queued_count = 0
        error_count = 0
        errors = []
        task_ids = []

        for story in stories:
            try:
                # Queue the blur data URL generation task
                task_result = story_generate_blur_data_url.delay(story.story_id)
                task_ids.append(task_result.id)
                queued_count += 1
                logger.info(
                    "Successfully queued blur data URL generation for "
                    "story: %s (task: %s)",
                    story.story_id,
                    task_result.id,
                )
            except Exception as e:
                error_count += 1
                error_msg = (
                    f"Failed to queue blur data URL generation for "
                    f"story {story.story_id}: {e!s}"
                )
                errors.append(error_msg)
                logger.exception(
                    "Error queuing blur data URL generation for story %s",
                    story.story_id,
                )

        logger.info(
            "Blur data URL generation queuing completed: "
            "%d queued, %d errors out of %d total stories",
            queued_count,
            error_count,
            total_stories,
        )

        return {  # noqa: TRY300
            "success": True,
            "message": "Blur data URL generation tasks queued",
            "total": total_stories,
            "queued": queued_count,
            "errors": error_count,
            "error_details": errors if errors else None,
            "task_ids": task_ids,
        }

    except Exception as e:
        logger.exception("Critical error in auto_generate_story_blur_data_urls")
        return {"success": False, "error": f"Critical error: {e!s}"}


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_story_thumbnail_insight(self, story_id: str) -> dict:
    """
    Generate AI-powered insight for a story thumbnail using OpenAI Vision API.
    This is a background task that calls the Story model's
    generate_thumbnail_insight method.

    Args:
        story_id (str): ID of the story to generate insight for

    Returns:
        dict: Operation result with success status and details
    """
    try:
        story = Story.objects.get(story_id=story_id)
    except Story.DoesNotExist:
        logger.exception("Story with ID %s not found", story_id)
        return {"success": False, "error": "Story not found"}

    # Check if thumbnail exists
    if not story.thumbnail:
        logger.warning(
            "No thumbnail file for story %s, cannot generate insight",
            story_id,
        )
        return {"success": False, "error": "No thumbnail file"}

    # Check if insight already exists
    if story.thumbnail_insight:
        logger.info("Thumbnail insight already exists for story %s", story_id)
        return {"success": True, "message": "Insight already exists"}

    try:
        # Generate the insight
        story.generate_thumbnail_insight()

        logger.info(
            "Successfully generated thumbnail insight for story %s (tokens: %s)",
            story_id,
            story.thumbnail_insight_token_usage,
        )

        return {  # noqa: TRY300
            "success": True,
            "message": "Successfully generated thumbnail insight",
            "story_id": story_id,
            "token_usage": story.thumbnail_insight_token_usage,
        }

    except ValueError as e:
        # Non-retryable error (e.g., thumbnail doesn't exist)
        logger.exception(
            "ValueError generating thumbnail insight for story %s",
            story_id,
        )
        return {"success": False, "error": f"ValueError: {e!s}"}

    except Exception as e:
        error_msg = str(e)

        # Determine if this is a retryable error
        retryable_keywords = [
            "network",
            "timeout",
            "connection",
            "502",
            "503",
            "504",
            "temporary",
            "rate limit",
            "api error",
            "openai",
        ]
        is_retryable = any(
            keyword in error_msg.lower() for keyword in retryable_keywords
        )

        if is_retryable and self.request.retries < self.max_retries:
            logger.warning(
                "Retryable error generating thumbnail insight for story %s "
                "(attempt %s/%s): %s",
                story_id,
                self.request.retries + 1,
                self.max_retries + 1,
                error_msg,
            )
            # Exponential backoff
            countdown = 60 * (2**self.request.retries)
            raise self.retry(exc=e, countdown=countdown) from e

        # Non-retryable error or max retries exceeded
        logger.exception(
            "Failed to generate thumbnail insight for story %s after %s attempts",
            story_id,
            self.request.retries + 1,
        )

        return {
            "success": False,
            "error": error_msg,
            "story_id": story_id,
            "attempts": self.request.retries + 1,
        }
