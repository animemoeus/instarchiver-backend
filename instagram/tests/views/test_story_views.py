from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from instagram.tests.factories import InstagramUserFactory
from instagram.tests.factories import StoryFactory


class StoryListViewTest(TestCase):
    """Test suite for StoryListView endpoint."""

    def setUp(self):
        """Set up test client and common test data."""
        self.client = APIClient()
        self.url = reverse("instagram:story_list")

    def test_list_stories_success(self):
        """Test successful retrieval of stories list."""
        expected_count = 5
        StoryFactory.create_batch(expected_count)

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert len(response.data["results"]) == expected_count

    def test_list_stories_unauthenticated_allowed(self):
        """Test unauthenticated access (IsAuthenticatedOrReadOnly)."""
        StoryFactory.create_batch(3)

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK

    def test_list_stories_pagination(self):
        """Test that pagination works correctly with cursor pagination."""
        # Create more stories than the default page size (20)
        default_page_size = 20
        StoryFactory.create_batch(25)

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert "next" in response.data
        assert "previous" in response.data
        assert len(response.data["results"]) == default_page_size

    def test_list_stories_with_page_size_param(self):
        """Test custom page size parameter."""
        custom_page_size = 5
        StoryFactory.create_batch(15)

        response = self.client.get(self.url, {"page_size": custom_page_size})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == custom_page_size

    def test_list_stories_max_page_size(self):
        """Test that max page size is enforced (100)."""
        max_page_size = 100
        StoryFactory.create_batch(150)

        response = self.client.get(self.url, {"page_size": 200})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) <= max_page_size

    def test_list_stories_ordering_default(self):
        """Test default ordering by created_at descending."""
        StoryFactory.create_batch(5)

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]

        # Most recent story should be first
        created_at_values = [story["created_at"] for story in results]
        assert created_at_values == sorted(created_at_values, reverse=True)

    def test_response_structure(self):
        """Test that the response contains expected fields."""
        StoryFactory()

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert len(results) > 0

        first_story = results[0]
        expected_fields = [
            "story_id",
            "user",
            "thumbnail",
            "media",
            "created_at",
            "story_created_at",
        ]

        for field in expected_fields:
            assert field in first_story, f"Field '{field}' missing from response"

    def test_nested_user_structure(self):
        """Test that nested user object contains expected fields."""
        user = InstagramUserFactory(username="testuser")
        StoryFactory(user=user)

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert len(results) > 0

        first_story = results[0]
        user_data = first_story["user"]

        expected_user_fields = [
            "uuid",
            "instagram_id",
            "username",
            "full_name",
            "profile_picture",
            "biography",
            "is_private",
            "is_verified",
            "media_count",
            "follower_count",
            "following_count",
            "allow_auto_update_stories",
            "allow_auto_update_profile",
            "created_at",
            "updated_at",
            "api_updated_at",
            "has_stories",
            "has_history",
        ]

        for field in expected_user_fields:
            assert field in user_data, f"Field '{field}' missing from user data"

    def test_user_has_stories_annotation(self):
        """Test that user's has_stories annotation is correct."""
        user = InstagramUserFactory(username="storyuser")
        StoryFactory(user=user)

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert len(results) > 0

        first_story = results[0]
        assert first_story["user"]["has_stories"] is True

    def test_user_has_history_annotation(self):
        """Test that user's has_history annotation is correct."""
        user = InstagramUserFactory(username="historyuser", full_name="Original Name")
        user.full_name = "Updated Name"
        user.save()

        StoryFactory(user=user)

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert len(results) > 0

        first_story = results[0]
        assert first_story["user"]["has_history"] is True

    def test_empty_list(self):
        """Test response when no stories exist."""
        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert len(response.data["results"]) == 0

    def test_cursor_pagination_next_page(self):
        """Test navigating to the next page using cursor pagination."""
        page_size = 10
        StoryFactory.create_batch(25)

        # Get first page
        response = self.client.get(self.url, {"page_size": page_size})
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == page_size
        assert response.data["next"] is not None

        # Extract cursor from next URL
        next_url = response.data["next"]
        cursor_start = next_url.find("cursor=") + 7
        cursor_end = next_url.find("&", cursor_start)
        if cursor_end == -1:
            cursor = next_url[cursor_start:]
        else:
            cursor = next_url[cursor_start:cursor_end]

        # Get second page
        response = self.client.get(
            self.url,
            {"page_size": page_size, "cursor": cursor},
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == page_size

    def test_stories_from_multiple_users(self):
        """Test that stories from multiple users are returned correctly."""
        user1 = InstagramUserFactory(username="user1")
        user2 = InstagramUserFactory(username="user2")

        StoryFactory.create_batch(3, user=user1)
        StoryFactory.create_batch(2, user=user2)

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert len(results) == 5  # noqa: PLR2004

        # Verify we have stories from both users
        usernames = {story["user"]["username"] for story in results}
        assert "user1" in usernames
        assert "user2" in usernames

    def test_story_with_same_user_multiple_times(self):
        """Test that the same user appears correctly in multiple stories."""
        user = InstagramUserFactory(username="multiuser")
        StoryFactory.create_batch(3, user=user)

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert len(results) == 3  # noqa: PLR2004

        # All stories should have the same user
        for story in results:
            assert story["user"]["username"] == "multiuser"
            assert story["user"]["uuid"] == str(user.uuid)


class StoryDetailViewTest(TestCase):
    """Test suite for StoryDetailView endpoint."""

    def setUp(self):
        """Set up test client and common test data."""
        self.client = APIClient()

    def test_retrieve_story_success(self):
        """Test successful retrieval of a single story."""
        user = InstagramUserFactory(username="testuser")
        story = StoryFactory(user=user)

        url = reverse("instagram:story_detail", kwargs={"story_id": story.story_id})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["story_id"] == story.story_id

    def test_retrieve_story_not_found(self):
        """Test retrieving a non-existent story returns 404."""
        url = reverse(
            "instagram:story_detail",
            kwargs={"story_id": "9999999999999999999"},
        )
        response = self.client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_story_unauthenticated_allowed(self):
        """Test unauthenticated access (IsAuthenticatedOrReadOnly)."""
        story = StoryFactory()

        url = reverse("instagram:story_detail", kwargs={"story_id": story.story_id})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK

    def test_response_structure(self):
        """Test that the response contains expected fields."""
        story = StoryFactory()

        url = reverse("instagram:story_detail", kwargs={"story_id": story.story_id})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK

        expected_fields = [
            "story_id",
            "user",
            "thumbnail",
            "media",
            "created_at",
            "story_created_at",
        ]

        for field in expected_fields:
            assert field in response.data, f"Field '{field}' missing from response"

    def test_nested_user_detail_structure(self):
        """Test that nested user object contains detailed fields."""
        user = InstagramUserFactory(username="detailuser")
        story = StoryFactory(user=user)

        url = reverse("instagram:story_detail", kwargs={"story_id": story.story_id})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        user_data = response.data["user"]

        expected_user_fields = [
            "uuid",
            "instagram_id",
            "username",
            "full_name",
            "profile_picture",
            "biography",
            "is_private",
            "is_verified",
            "media_count",
            "follower_count",
            "following_count",
            "allow_auto_update_stories",
            "allow_auto_update_profile",
            "auto_update_stories_limit_count",
            "auto_update_profile_limit_count",
            "created_at",
            "updated_at",
            "updated_at_from_api",
            "has_stories",
            "has_history",
        ]

        for field in expected_user_fields:
            assert field in user_data, f"Field '{field}' missing from user data"

    def test_user_has_stories_annotation(self):
        """Test that user's has_stories annotation is correct."""
        user = InstagramUserFactory(username="storyuser")
        story = StoryFactory(user=user)

        url = reverse("instagram:story_detail", kwargs={"story_id": story.story_id})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["user"]["has_stories"] is True

    def test_user_has_history_annotation(self):
        """Test that user's has_history annotation is correct."""
        user = InstagramUserFactory(username="historyuser", full_name="Original Name")
        user.full_name = "Updated Name"
        user.save()

        story = StoryFactory(user=user)

        url = reverse("instagram:story_detail", kwargs={"story_id": story.story_id})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["user"]["has_history"] is True

    def test_user_without_history(self):
        """Test that newly created user has has_history as True.

        django-simple-history creates initial record on creation.
        """
        user = InstagramUserFactory(username="nohistoryuser")
        story = StoryFactory(user=user)

        url = reverse("instagram:story_detail", kwargs={"story_id": story.story_id})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # has_history is True because django-simple-history creates a record on creation
        assert response.data["user"]["has_history"] is True

    def test_story_id_field_matches(self):
        """Test that story_id in response matches the requested story."""
        story = StoryFactory()

        url = reverse("instagram:story_detail", kwargs={"story_id": story.story_id})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["story_id"] == story.story_id

    def test_user_uuid_field_matches(self):
        """Test that user UUID in response matches the story's user."""
        user = InstagramUserFactory()
        story = StoryFactory(user=user)

        url = reverse("instagram:story_detail", kwargs={"story_id": story.story_id})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["user"]["uuid"] == str(user.uuid)
