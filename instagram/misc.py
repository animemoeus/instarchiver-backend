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
