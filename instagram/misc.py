import uuid
from pathlib import Path


def get_user_profile_picture_upload_location(instance, filename):
    # Generate random UUID filename while preserving extension
    file_extension = Path(filename).suffix
    random_filename = str(uuid.uuid4())
    return f"users/{instance.username}/{random_filename}{file_extension}"


def get_user_story_upload_location(instance, filename):
    # Generate random UUID filename while preserving extension
    file_extension = Path(filename).suffix
    random_filename = str(uuid.uuid4())
    return f"users/{instance.user.username}/stories/{random_filename}{file_extension}"


def get_post_media_upload_location(instance, filename):
    # Generate random UUID filename while preserving extension
    file_extension = Path(filename).suffix
    random_filename = str(uuid.uuid4())
    # PostMedia accesses user via post.user, Post accesses user directly
    username = (
        instance.post.user.username
        if hasattr(instance, "post")
        else instance.user.username
    )
    return f"posts/{username}/{random_filename}{file_extension}"
