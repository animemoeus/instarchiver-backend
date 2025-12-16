from django.utils import timezone
from factory import Faker
from factory import LazyFunction
from factory import SubFactory
from factory.django import DjangoModelFactory

from instagram.models import Post
from instagram.models import PostMedia
from instagram.models import Story
from instagram.models import User as InstagramUser


class InstagramUserFactory(DjangoModelFactory):
    """Factory for creating Instagram User instances for testing."""

    instagram_id = Faker("numerify", text="##########")
    username = Faker("user_name")
    full_name = Faker("name")
    biography = Faker("text", max_nb_chars=150)
    original_profile_picture_url = Faker("numerify", text="https://placecats.com/##/##")
    is_private = Faker("boolean")
    is_verified = Faker("boolean", chance_of_getting_true=20)
    media_count = Faker("random_int", min=0, max=1000)
    follower_count = Faker("random_int", min=0, max=100000)
    following_count = Faker("random_int", min=0, max=5000)
    allow_auto_update_stories = Faker("boolean")
    allow_auto_update_profile = Faker("boolean")

    class Meta:
        model = InstagramUser
        django_get_or_create = ["username"]


class StoryFactory(DjangoModelFactory):
    """Factory for creating Story instances for testing."""

    story_id = Faker("numerify", text="###################")
    user = SubFactory(InstagramUserFactory)
    thumbnail_url = "https://cdn.instarchiver.net/users/arter_tendean/stories/6a2d71ab-80a5-477e-83a0-b4ea811816ff.jpg"
    blur_data_url = Faker("pystr", max_chars=100)
    media_url = "https://cdn.instarchiver.net/users/arter_tendean/stories/214d3932-ab14-45c2-874d-c5c65cdaf66e.mp4"
    story_created_at = Faker("date_time", tzinfo=timezone.get_current_timezone())

    class Meta:
        model = Story
        django_get_or_create = ["story_id"]


class PostFactory(DjangoModelFactory):
    """Factory for creating Post instances for testing."""

    id = Faker("numerify", text="###################")
    user = SubFactory(InstagramUserFactory)
    variant = Faker(
        "random_element",
        elements=[Post.POST_VARIANT_NORMAL, Post.POST_VARIANT_CAROUSEL],
    )
    thumbnail_url = "https://cdn.instarchiver.net/users/arter_tendean/posts/6a2d71ab-80a5-477e-83a0-b4ea811816ff.jpg"
    blur_data_url = Faker("pystr", max_chars=100)
    raw_data = LazyFunction(
        lambda: {
            "caption": "Test caption",
            "like_count": 100,
            "comment_count": 10,
        },
    )

    class Meta:
        model = Post
        django_get_or_create = ["id"]


class PostMediaFactory(DjangoModelFactory):
    """Factory for creating PostMedia instances for testing."""

    post = SubFactory(PostFactory)
    thumbnail_url = "https://cdn.instarchiver.net/users/arter_tendean/posts/6a2d71ab-80a5-477e-83a0-b4ea811816ff.jpg"
    media_url = "https://cdn.instarchiver.net/users/arter_tendean/posts/214d3932-ab14-45c2-874d-c5c65cdaf66e.mp4"

    class Meta:
        model = PostMedia
