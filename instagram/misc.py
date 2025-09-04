def get_user_profile_picture_upload_location(instance, filename):
    # File will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return f"users/{instance.username}/{filename}"
