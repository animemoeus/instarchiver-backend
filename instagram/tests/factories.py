from factory import Faker
from factory.django import DjangoModelFactory

from instagram.models import User as InstagramUser


class InstagramUserFactory(DjangoModelFactory):
    """Factory for creating Instagram User instances for testing."""

    instagram_id = Faker("numerify", text="##########")
    username = Faker("user_name")
    full_name = Faker("name")
    biography = Faker("text", max_nb_chars=150)
    original_profile_picture_url = Faker("image_url")
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
