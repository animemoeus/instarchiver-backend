import hashlib
import logging

import requests
from celery import shared_task
from django.core.files.base import ContentFile

from instagram.models import Post
from instagram.models import PostMedia
from instagram.utils import generate_blur_data_url_from_image_url

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def post_generate_blur_data_url(self, post_id: str) -> dict:
    """
    Generate blur data URL for a post in the background.
    Delegates business logic to the utility function.

    Args:
        post_id (str): ID of the post to generate blur data URL for

    Returns:
        dict: Operation result with success status and details
    """
    try:
        post = Post.objects.get(id=post_id)
    except Post.DoesNotExist:
        logger.exception("Post with ID %s not found", post_id)
        return {"success": False, "error": "Post not found"}

    try:
        # Generate blur data URL using utility function
        blur_data_url = generate_blur_data_url_from_image_url(
            post.thumbnail.url if post.thumbnail else post.thumbnail_url,
        )

        # Save to the model
        post.blur_data_url = blur_data_url
        post.save()

        logger.info(
            "Successfully generated blur data URL for post %s",
            post_id,
        )

        return {  # noqa: TRY300
            "success": True,
            "message": "Successfully generated blur data URL",
            "post_id": post_id,
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
                "Retryable error generating blur data URL for post %s "
                "(attempt %s/%s): %s",
                post_id,
                self.request.retries + 1,
                self.max_retries + 1,
                error_msg,
            )
            # Exponential backoff
            countdown = 60 * (2**self.request.retries)
            raise self.retry(exc=e, countdown=countdown) from e

        # Non-retryable error or max retries exceeded
        logger.exception(
            "Failed to generate blur data URL for post %s after %s attempts",
            post_id,
            self.request.retries + 1,
        )

        return {
            "success": False,
            "error": error_msg,
            "post_id": post_id,
            "attempts": self.request.retries + 1,
        }


@shared_task
def periodic_generate_post_blur_data_urls():
    """
    Automatically generate blur data URLs for posts that don't have them yet.
    This task is designed to be run periodically via Celery Beat.

    Returns:
        dict: Summary of operations performed
    """
    try:
        # Get all posts without blur_data_url
        posts = Post.objects.filter(blur_data_url="")
        total_posts = posts.count()

        if total_posts == 0:
            logger.info("No posts found without blur data URL")
            return {
                "success": True,
                "message": "No posts to process",
                "queued": 0,
                "errors": 0,
            }

        logger.info(
            "Starting blur data URL generation for %d posts",
            total_posts,
        )

        queued_count = 0
        error_count = 0
        errors = []
        task_ids = []

        for post in posts:
            try:
                # Queue the blur data URL generation task
                task_result = post_generate_blur_data_url.delay(post.id)
                task_ids.append(task_result.id)
                queued_count += 1
                logger.info(
                    "Successfully queued blur data URL generation for "
                    "post: %s (task: %s)",
                    post.id,
                    task_result.id,
                )
            except Exception as e:
                error_count += 1
                error_msg = (
                    f"Failed to queue blur data URL generation for "
                    f"post {post.id}: {e!s}"
                )
                errors.append(error_msg)
                logger.exception(
                    "Error queuing blur data URL generation for post %s",
                    post.id,
                )

        logger.info(
            "Blur data URL generation queuing completed: "
            "%d queued, %d errors out of %d total posts",
            queued_count,
            error_count,
            total_posts,
        )

        return {  # noqa: TRY300
            "success": True,
            "message": "Blur data URL generation tasks queued",
            "total": total_posts,
            "queued": queued_count,
            "errors": error_count,
            "error_details": errors if errors else None,
            "task_ids": task_ids,
        }

    except Exception as e:
        logger.exception("Critical error in periodic_generate_post_blur_data_urls")
        return {"success": False, "error": f"Critical error: {e!s}"}


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def download_post_thumbnail_from_url(self, post_id):
    """
    Download post thumbnail from URL if content has changed.
    Uses hash comparison to detect actual image content changes.

    Args:
        post_id (str): ID of the post to download thumbnail for

    Returns:
        dict: Operation result with success status and details
    """
    try:
        post = Post.objects.get(id=post_id)
    except Post.DoesNotExist:
        logger.exception("Post with ID %s not found", post_id)
        return {"success": False, "error": "Post not found"}

    if not post.thumbnail_url:
        logger.info("No thumbnail URL for post %s", post_id)
        return {"success": False, "error": "No thumbnail URL"}

    try:
        # Download image from URL
        response = requests.get(post.thumbnail_url, timeout=30)
        response.raise_for_status()

        # Calculate hash of downloaded image content
        new_image_content = response.content
        new_image_hash = hashlib.sha256(new_image_content).hexdigest()

        # Get hash of existing thumbnail if it exists
        existing_image_hash = None
        if post.thumbnail:
            try:
                with post.thumbnail.open("rb") as f:
                    existing_content = f.read()
                    existing_image_hash = hashlib.sha256(existing_content).hexdigest()
            except OSError as e:
                logger.warning(
                    "Could not read existing thumbnail for post %s: %s",
                    post_id,
                    e,
                )

        # Compare hashes - only update if different
        if existing_image_hash == new_image_hash:
            logger.info("Thumbnail unchanged for post %s", post_id)
            return {"success": True, "message": "No changes detected"}

        # Save new image
        filename = f"post_{post_id}_thumbnail.jpg"

        # Save the new image
        post.thumbnail.save(
            filename,
            ContentFile(new_image_content),
            save=False,
        )

        # Update using queryset to avoid triggering signal again
        Post.objects.filter(id=post.id).update(
            thumbnail=post.thumbnail.name,
        )

        logger.info("Thumbnail downloaded for post %s", post_id)
        return {  # noqa: TRY300
            "success": True,
            "message": "Thumbnail downloaded",
            "old_hash": existing_image_hash,
            "new_hash": new_image_hash,
        }

    except (requests.RequestException, OSError) as e:
        # Retryable errors: network issues, S3 timeouts, temporary file access issues
        logger.warning(
            "Retryable error downloading thumbnail for post %s (attempt %s/%s): %s",
            post_id,
            self.request.retries + 1,
            self.max_retries + 1,
            e,
        )
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (2**self.request.retries)) from e

        logger.exception(
            "Max retries exceeded for thumbnail download for post %s",
            post_id,
        )
        return {"success": False, "error": f"Max retries exceeded: {e!s}"}

    except Exception as e:
        # Non-retryable errors: permanent failures
        logger.exception(
            "Permanent error downloading thumbnail for post %s",
            post_id,
        )
        return {"success": False, "error": f"Permanent error: {e!s}"}


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def download_post_media_thumbnail_from_url(self, post_media_id):
    """
    Download post media thumbnail from URL if content has changed.
    Uses hash comparison to detect actual image content changes.

    Args:
        post_media_id (int): ID of the post media to download thumbnail for

    Returns:
        dict: Operation result with success status and details
    """
    try:
        post_media = PostMedia.objects.get(id=post_media_id)
    except PostMedia.DoesNotExist:
        logger.exception("PostMedia with ID %s not found", post_media_id)
        return {"success": False, "error": "PostMedia not found"}

    if not post_media.thumbnail_url:
        logger.info("No thumbnail URL for post media %s", post_media_id)
        return {"success": False, "error": "No thumbnail URL"}

    try:
        # Download image from URL
        response = requests.get(post_media.thumbnail_url, timeout=30)
        response.raise_for_status()

        # Calculate hash of downloaded image content
        new_image_content = response.content
        new_image_hash = hashlib.sha256(new_image_content).hexdigest()

        # Get hash of existing thumbnail if it exists
        existing_image_hash = None
        if post_media.thumbnail:
            try:
                with post_media.thumbnail.open("rb") as f:
                    existing_content = f.read()
                    existing_image_hash = hashlib.sha256(existing_content).hexdigest()
            except OSError as e:
                logger.warning(
                    "Could not read existing thumbnail for post media %s: %s",
                    post_media_id,
                    e,
                )

        # Compare hashes - only update if different
        if existing_image_hash == new_image_hash:
            logger.info("Thumbnail unchanged for post media %s", post_media_id)
            return {"success": True, "message": "No changes detected"}

        # Save new image
        filename = f"post_media_{post_media_id}_thumbnail.jpg"

        # Save the new image
        post_media.thumbnail.save(
            filename,
            ContentFile(new_image_content),
            save=False,
        )

        # Update using queryset to avoid triggering signal again
        PostMedia.objects.filter(id=post_media.id).update(
            thumbnail=post_media.thumbnail.name,
        )

        logger.info("Thumbnail downloaded for post media %s", post_media_id)
        return {  # noqa: TRY300
            "success": True,
            "message": "Thumbnail downloaded",
            "old_hash": existing_image_hash,
            "new_hash": new_image_hash,
        }

    except (requests.RequestException, OSError) as e:
        # Retryable errors: network issues, S3 timeouts, temporary file access issues
        logger.warning(
            "Retryable error downloading thumbnail for post media %s "
            "(attempt %s/%s): %s",
            post_media_id,
            self.request.retries + 1,
            self.max_retries + 1,
            e,
        )
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (2**self.request.retries)) from e

        logger.exception(
            "Max retries exceeded for thumbnail download for post media %s",
            post_media_id,
        )
        return {"success": False, "error": f"Max retries exceeded: {e!s}"}

    except Exception as e:
        # Non-retryable errors: permanent failures
        logger.exception(
            "Permanent error downloading thumbnail for post media %s",
            post_media_id,
        )
        return {"success": False, "error": f"Permanent error: {e!s}"}
