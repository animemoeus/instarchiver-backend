"""Instagram admin configuration."""

from .post import PostAdmin
from .post_media import PostMediaAdmin
from .story import StoryAdmin
from .story_credit import StoryCreditAdmin
from .story_credit_payment import StoryCreditPaymentAdmin
from .user import InstagramUserAdmin
from .user_update_story_log import UserUpdateStoryLogAdmin

__all__ = [
    "InstagramUserAdmin",
    "PostAdmin",
    "PostMediaAdmin",
    "StoryAdmin",
    "StoryCreditAdmin",
    "StoryCreditPaymentAdmin",
    "UserUpdateStoryLogAdmin",
]
