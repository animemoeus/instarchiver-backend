"""Generate thumbnail insights for existing posts using Celery tasks.

This script queues thumbnail insight generation tasks for posts that have
thumbnails but no insights yet. It uses the existing Celery task infrastructure
for proper error handling and retry logic.

Usage:
    # Dry run (shows what would be processed)
    python manage.py runscript generate_thumbnail_insights --script-args --dry-run

    # Process all posts
    python manage.py runscript generate_thumbnail_insights

    # Process with batch limit
    python manage.py runscript generate_thumbnail_insights --script-args --limit=10
"""  # noqa: INP001

import sys

from instagram.models import Post
from instagram.tasks.post import generate_post_thumbnail_insight


def _parse_arguments(args):
    """Parse command line arguments."""
    dry_run = "--dry-run" in args
    limit = None

    for arg in args:
        if arg.startswith("--limit="):
            try:
                limit = int(arg.split("=")[1])
            except (ValueError, IndexError):
                print("Error: Invalid limit value. Use --limit=N")  # noqa: T201
                sys.exit(1)

    return dry_run, limit


def _print_dry_run_summary(posts):
    """Print summary for dry run mode."""
    print("\n🔍 DRY RUN - No tasks will be queued\n")  # noqa: T201
    for i, post in enumerate(posts, 1):
        print(  # noqa: T201
            f"{i}. Post {post.id} ({post.user.username}) - "
            f"Created: {post.created_at.strftime('%Y-%m-%d %H:%M')}",
        )
    print(f"\nWould queue {posts.count()} tasks")  # noqa: T201


def _queue_insight_tasks(posts):
    """Queue thumbnail insight generation tasks for posts."""
    print("\n🚀 Queuing thumbnail insight generation tasks...\n")  # noqa: T201

    queued_count = 0
    error_count = 0
    total_count = posts.count()

    for i, post in enumerate(posts, 1):
        try:
            task_result = generate_post_thumbnail_insight.delay(post.id)
            queued_count += 1
            print(  # noqa: T201
                f"✓ {i}/{total_count} Post {post.id} "
                f"({post.user.username}) - Task: {task_result.id}",
            )
        except Exception as e:  # noqa: BLE001
            error_count += 1
            print(  # noqa: T201
                f"✗ {i}/{total_count} Post {post.id} - Error: {e}",
            )

    return queued_count, error_count, total_count


def run(*args):
    """Queue thumbnail insight generation tasks for existing posts."""
    dry_run, limit = _parse_arguments(args)

    # Find posts that need insights
    posts = Post.objects.filter(
        thumbnail__isnull=False,  # Has thumbnail file
        thumbnail_insight="",  # No insight yet
    ).order_by("-created_at")

    if limit:
        posts = posts[:limit]

    total_count = posts.count()

    if total_count == 0:
        print("✓ No posts found that need thumbnail insights!")  # noqa: T201
        return

    print(f"Found {total_count} posts that need thumbnail insights")  # noqa: T201

    if dry_run:
        _print_dry_run_summary(posts)
        return

    # Queue tasks
    queued_count, error_count, total_count = _queue_insight_tasks(posts)

    # Summary
    print(f"\n{'=' * 60}")  # noqa: T201
    print("Summary:")  # noqa: T201
    print(f"  Total posts: {total_count}")  # noqa: T201
    print(f"  Tasks queued: {queued_count}")  # noqa: T201
    print(f"  Errors: {error_count}")  # noqa: T201
    print(f"{'=' * 60}\n")  # noqa: T201

    if queued_count > 0:
        print("✓ Tasks queued successfully!")  # noqa: T201
        print(  # noqa: T201
            "Monitor progress in Celery Flower: http://localhost:5555",
        )
        print("\nNote: Tasks will run in the background with retry logic.")  # noqa: T201
        print(  # noqa: T201
            "Check logs for detailed progress and any errors.",
        )
