import uuid

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from instagram.models import Story
from instagram.tests.factories import InstagramUserFactory


class InstagramUserListViewTest(TestCase):
    """Test suite for InstagramUserListView endpoint."""

    def setUp(self):
        """Set up test client and common test data."""
        self.client = APIClient()
        self.url = reverse("instagram:user_list")

    def test_list_users_success(self):
        """Test successful retrieval of Instagram users list."""
        expected_count = 5
        for i in range(expected_count):
            InstagramUserFactory(
                username=f"testuser{i}",
                full_name=f"Test User {i}",
                biography=f"Bio for user {i}",
            )

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert len(response.data["results"]) == expected_count

    def test_list_users_unauthenticated_allowed(self):
        """Test unauthenticated access (IsAuthenticatedOrReadOnly)."""
        InstagramUserFactory.create_batch(3)

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK

    def test_list_users_pagination(self):
        """Test that pagination works correctly with cursor pagination."""
        # Create more users than the default page size (20)
        default_page_size = 20
        InstagramUserFactory.create_batch(25)

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert "next" in response.data
        assert "previous" in response.data
        assert len(response.data["results"]) == default_page_size

    def test_list_users_with_page_size_param(self):
        """Test custom page size parameter."""
        custom_page_size = 5
        InstagramUserFactory.create_batch(15)

        response = self.client.get(self.url, {"page_size": custom_page_size})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == custom_page_size

    def test_list_users_max_page_size(self):
        """Test that max page size is enforced (100)."""
        max_page_size = 100
        InstagramUserFactory.create_batch(150)

        response = self.client.get(self.url, {"page_size": 200})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) <= max_page_size

    def test_list_users_ordering_default(self):
        """Test default ordering by created_at descending."""
        InstagramUserFactory.create_batch(5)

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]

        # Most recent user should be first
        created_at_values = [user["created_at"] for user in results]
        assert created_at_values == sorted(created_at_values, reverse=True)

    def test_list_users_ordering_by_username(self):
        """Test ordering by username."""
        InstagramUserFactory.create_batch(5)

        response = self.client.get(self.url, {"ordering": "username"})

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]

        usernames = [user["username"] for user in results]
        assert usernames == sorted(usernames)

    def test_list_users_ordering_by_full_name_desc(self):
        """Test ordering by full_name descending."""
        InstagramUserFactory.create_batch(5)

        response = self.client.get(self.url, {"ordering": "-full_name"})

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]

        full_names = [user["full_name"] for user in results]
        assert full_names == sorted(full_names, reverse=True)

    def test_search_by_username(self):
        """Test searching users by username."""
        InstagramUserFactory.create_batch(5)
        InstagramUserFactory(username="uniqueusername123")

        response = self.client.get(self.url, {"search": "uniqueusername123"})

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert len(results) == 1
        assert results[0]["username"] == "uniqueusername123"

    def test_search_by_full_name(self):
        """Test searching users by full name."""
        InstagramUserFactory.create_batch(3)
        InstagramUserFactory(
            username="searchuser",
            full_name="John Unique Doe",
        )

        response = self.client.get(self.url, {"search": "John Unique Doe"})

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert len(results) >= 1
        assert any(user["full_name"] == "John Unique Doe" for user in results)

    def test_search_by_biography(self):
        """Test searching users by biography."""
        InstagramUserFactory.create_batch(3)
        InstagramUserFactory(
            username="biouser",
            biography="This is a unique biography text",
        )

        response = self.client.get(self.url, {"search": "unique biography text"})

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert len(results) >= 1
        assert any("unique biography text" in user["biography"] for user in results)

    def test_search_no_results(self):
        """Test searching with no matching results."""
        InstagramUserFactory.create_batch(3)

        response = self.client.get(self.url, {"search": "nonexistent_user_xyz_12345"})

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert len(results) == 0

    def test_has_stories_annotation(self):
        """Test that has_stories annotation is present and correct."""
        # Create user with stories
        user_with_stories = InstagramUserFactory(username="storyuser")
        Story.objects.create(
            story_id="story123",
            user=user_with_stories,
            thumbnail_url="https://example.com/thumb.jpg",
            media_url="https://example.com/media.jpg",
            story_created_at="2025-01-01T00:00:00Z",
        )

        # Create user without stories
        InstagramUserFactory(username="nostoryuser")

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]

        # Find both users in results
        user_with_stories_data = next(
            (u for u in results if u["username"] == "storyuser"),
            None,
        )
        user_without_stories_data = next(
            (u for u in results if u["username"] == "nostoryuser"),
            None,
        )

        assert user_with_stories_data is not None
        assert user_without_stories_data is not None
        assert user_with_stories_data["has_stories"] is True
        assert user_without_stories_data["has_stories"] is False

    def test_has_history_annotation(self):
        """Test that has_history annotation is present and correct."""
        # Create user and trigger a historical record
        user = InstagramUserFactory(username="historyuser", full_name="Original Name")
        user.full_name = "Updated Name"
        user.save()

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]

        user_data = next((u for u in results if u["username"] == "historyuser"), None)
        assert user_data is not None
        assert "has_history" in user_data
        assert user_data["has_history"] is True

    def test_response_structure(self):
        """Test that the response contains expected fields."""
        InstagramUserFactory(username="testuser")

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert len(results) > 0

        first_user = results[0]
        expected_fields = [
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

        for field in expected_fields:
            assert field in first_user, f"Field '{field}' missing from response"

    def test_excluded_fields_not_in_response(self):
        """Test that excluded fields are not in the list response."""
        InstagramUserFactory(username="testuser")

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert len(results) > 0

        first_user = results[0]
        excluded_fields = ["original_profile_picture_url", "raw_api_data"]

        for field in excluded_fields:
            assert field not in first_user, (
                f"Excluded field '{field}' should not be in response"
            )

    def test_empty_list(self):
        """Test response when no users exist."""
        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert len(response.data["results"]) == 0

    def test_combined_search_and_ordering(self):
        """Test combining search and ordering parameters."""
        expected_match_count = 3
        InstagramUserFactory(username="testuser1", full_name="Alice")
        InstagramUserFactory(username="testuser2", full_name="Bob")
        InstagramUserFactory(username="testuser3", full_name="Charlie")
        InstagramUserFactory(username="otheruser", full_name="David")

        response = self.client.get(
            self.url,
            {"search": "testuser", "ordering": "username"},
        )

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert len(results) == expected_match_count

        usernames = [user["username"] for user in results]
        assert usernames == sorted(usernames)
        assert all("testuser" in username for username in usernames)

    def test_cursor_pagination_next_page(self):
        """Test navigating to the next page using cursor pagination."""
        page_size = 10
        InstagramUserFactory.create_batch(25)

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

    def test_filter_and_order_fields_allowed(self):
        """Test that all ordering fields defined in the view work correctly."""
        InstagramUserFactory.create_batch(5)

        # Test all allowed ordering fields
        ordering_fields = ["created_at", "updated_at", "username", "full_name"]

        for field in ordering_fields:
            # Test ascending
            response = self.client.get(self.url, {"ordering": field})
            assert response.status_code == status.HTTP_200_OK

            # Test descending
            response = self.client.get(self.url, {"ordering": f"-{field}"})
            assert response.status_code == status.HTTP_200_OK


class InstagramUserDetailViewTest(TestCase):
    """Test suite for InstagramUserDetailView endpoint."""

    def setUp(self):
        """Set up test client and common test data."""
        self.client = APIClient()

    def test_retrieve_user_success(self):
        """Test successful retrieval of a user by UUID."""
        user = InstagramUserFactory(
            username="testuser",
            full_name="Test User",
            biography="Test bio",
        )

        url = reverse("instagram:user_detail", kwargs={"uuid": user.uuid})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["uuid"] == str(user.uuid)
        assert response.data["username"] == "testuser"
        assert response.data["full_name"] == "Test User"
        assert response.data["biography"] == "Test bio"

    def test_retrieve_user_not_found(self):
        """Test 404 response for non-existent UUID."""

        non_existent_uuid = uuid.uuid4()
        url = reverse("instagram:user_detail", kwargs={"uuid": non_existent_uuid})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_user_unauthenticated_allowed(self):
        """Test that unauthenticated users can access the endpoint."""
        user = InstagramUserFactory(username="publicuser")

        url = reverse("instagram:user_detail", kwargs={"uuid": user.uuid})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["username"] == "publicuser"

    def test_response_structure(self):
        """Test that the response contains all expected fields."""
        user = InstagramUserFactory(username="testuser")

        url = reverse("instagram:user_detail", kwargs={"uuid": user.uuid})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK

        expected_fields = [
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
            "updated_at_from_api",
            "has_stories",
            "has_history",
            "auto_update_stories_limit_count",
            "auto_update_profile_limit_count",
        ]

        for field in expected_fields:
            assert field in response.data, f"Field '{field}' missing from response"

    def test_excluded_fields_not_in_response(self):
        """Test that excluded fields are not in the detail response."""
        user = InstagramUserFactory(username="testuser")

        url = reverse("instagram:user_detail", kwargs={"uuid": user.uuid})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK

        excluded_fields = ["original_profile_picture_url", "raw_api_data"]

        for field in excluded_fields:
            assert field not in response.data, (
                f"Excluded field '{field}' should not be in response"
            )

    def test_has_stories_annotation(self):
        """Test that has_stories annotation is present and correct."""
        # Create user with stories
        user_with_stories = InstagramUserFactory(username="storyuser")
        Story.objects.create(
            story_id="story123",
            user=user_with_stories,
            thumbnail_url="https://example.com/thumb.jpg",
            media_url="https://example.com/media.jpg",
            story_created_at="2025-01-01T00:00:00Z",
        )

        # Create user without stories
        user_without_stories = InstagramUserFactory(username="nostoryuser")

        # Test user with stories
        url = reverse("instagram:user_detail", kwargs={"uuid": user_with_stories.uuid})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["has_stories"] is True

        # Test user without stories
        url = reverse(
            "instagram:user_detail",
            kwargs={"uuid": user_without_stories.uuid},
        )
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["has_stories"] is False

    def test_has_history_annotation(self):
        """Test that has_history annotation is present and correct."""
        # Create user and trigger a historical record
        user = InstagramUserFactory(username="historyuser", full_name="Original Name")
        user.full_name = "Updated Name"
        user.save()

        url = reverse("instagram:user_detail", kwargs={"uuid": user.uuid})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "has_history" in response.data
        assert response.data["has_history"] is True

    def test_auto_update_limit_count_fields(self):
        """Test that auto_update_*_limit_count fields return 0."""
        user = InstagramUserFactory(username="testuser")

        url = reverse("instagram:user_detail", kwargs={"uuid": user.uuid})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["auto_update_stories_limit_count"] == 0
        assert response.data["auto_update_profile_limit_count"] == 0

    def test_updated_at_from_api_field(self):
        """Test that api_updated_at is renamed to updated_at_from_api in response."""

        user = InstagramUserFactory(username="testuser")
        user.api_updated_at = timezone.now()
        user.save()

        url = reverse("instagram:user_detail", kwargs={"uuid": user.uuid})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "updated_at_from_api" in response.data
        assert "api_updated_at" not in response.data
        assert response.data["updated_at_from_api"] is not None


class InstagramUserHistoryViewTest(TestCase):
    """Test suite for InstagramUserHistoryView endpoint."""

    def setUp(self):
        """Set up test client and common test data."""
        self.client = APIClient()

    def test_retrieve_user_history_success(self):
        """Test successful retrieval of user history."""
        # Create user and make several updates to generate history
        user = InstagramUserFactory(
            username="testuser",
            full_name="Original Name",
            biography="Original bio",
        )

        # Make updates to create history records
        user.full_name = "Updated Name 1"
        user.save()

        user.biography = "Updated bio"
        user.save()

        user.full_name = "Updated Name 2"
        user.save()

        url = reverse("instagram:user_history", kwargs={"uuid": user.uuid})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        # Should have 4 records: initial creation + 3 updates
        assert len(response.data["results"]) == 4  # noqa: PLR2004

    def test_retrieve_user_history_not_found(self):
        """Test 404 response when user has no history."""
        non_existent_uuid = uuid.uuid4()
        url = reverse("instagram:user_history", kwargs={"uuid": non_existent_uuid})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert len(response.data["results"]) == 0

    def test_retrieve_user_history_unauthenticated_allowed(self):
        """Test that unauthenticated users can access the endpoint."""
        user = InstagramUserFactory(username="publicuser")
        user.full_name = "Updated Name"
        user.save()

        url = reverse("instagram:user_history", kwargs={"uuid": user.uuid})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1

    def test_history_ordering_by_date_descending(self):
        """Test that history is ordered by history_date descending (most recent first)."""  # noqa: E501
        user = InstagramUserFactory(username="testuser", full_name="Original")

        # Make multiple updates
        user.full_name = "Update 1"
        user.save()

        user.full_name = "Update 2"
        user.save()

        user.full_name = "Update 3"
        user.save()

        url = reverse("instagram:user_history", kwargs={"uuid": user.uuid})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]

        # Most recent change should be first
        assert results[0]["full_name"] == "Update 3"
        assert results[1]["full_name"] == "Update 2"
        assert results[2]["full_name"] == "Update 1"
        assert results[3]["full_name"] == "Original"

    def test_history_pagination(self):
        """Test that pagination works correctly with cursor pagination."""
        user = InstagramUserFactory(username="testuser")

        # Create more history records than the default page size (20)
        for i in range(25):
            user.full_name = f"Update {i}"
            user.save()

        url = reverse("instagram:user_history", kwargs={"uuid": user.uuid})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert "next" in response.data
        assert "previous" in response.data
        # Should have default page size (20) + initial creation = 21, but capped at 20
        assert len(response.data["results"]) == 20  # noqa: PLR2004

    def test_history_with_custom_page_size(self):
        """Test custom page size parameter."""
        user = InstagramUserFactory(username="testuser")

        # Create 15 updates
        for i in range(15):
            user.full_name = f"Update {i}"
            user.save()

        custom_page_size = 5
        url = reverse("instagram:user_history", kwargs={"uuid": user.uuid})
        response = self.client.get(url, {"page_size": custom_page_size})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == custom_page_size

    def test_history_max_page_size(self):
        """Test that max page size is enforced (100)."""
        user = InstagramUserFactory(username="testuser")

        # Create many updates
        for i in range(110):
            user.full_name = f"Update {i}"
            user.save()

        max_page_size = 100
        url = reverse("instagram:user_history", kwargs={"uuid": user.uuid})
        response = self.client.get(url, {"page_size": 200})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) <= max_page_size

    def test_history_response_structure(self):
        """Test that the response contains all expected fields."""
        user = InstagramUserFactory(username="testuser")
        user.full_name = "Updated Name"
        user.save()

        url = reverse("instagram:user_history", kwargs={"uuid": user.uuid})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert len(results) > 0

        first_record = results[0]
        expected_fields = [
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
            "history_id",
            "history_date",
            "history_change_reason",
            "history_type",
        ]

        for field in expected_fields:
            assert field in first_record, f"Field '{field}' missing from response"

    def test_history_excluded_fields(self):
        """Test that excluded fields are not in the history response."""
        user = InstagramUserFactory(username="testuser")
        user.full_name = "Updated Name"
        user.save()

        url = reverse("instagram:user_history", kwargs={"uuid": user.uuid})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert len(results) > 0

        first_record = results[0]
        excluded_fields = [
            "original_profile_picture_url",
            "raw_api_data",
            "history_user",
        ]

        for field in excluded_fields:
            assert field not in first_record, (
                f"Excluded field '{field}' should not be in response"
            )

    def test_history_type_field(self):
        """Test that history_type field correctly identifies the change type."""
        user = InstagramUserFactory(username="testuser")

        url = reverse("instagram:user_history", kwargs={"uuid": user.uuid})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]

        # First record should be creation (+)
        assert results[-1]["history_type"] == "+"

        # Make an update
        user.full_name = "Updated Name"
        user.save()

        response = self.client.get(url)
        results = response.data["results"]

        # Most recent should be update (~)
        assert results[0]["history_type"] == "~"

    def test_history_cursor_pagination_next_page(self):
        """Test navigating to the next page using cursor pagination."""
        user = InstagramUserFactory(username="testuser")

        # Create 25 updates
        for i in range(25):
            user.full_name = f"Update {i}"
            user.save()

        page_size = 10
        url = reverse("instagram:user_history", kwargs={"uuid": user.uuid})

        # Get first page
        response = self.client.get(url, {"page_size": page_size})
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
        response = self.client.get(url, {"page_size": page_size, "cursor": cursor})
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == page_size

    def test_history_tracks_field_changes(self):
        """Test that history correctly tracks specific field changes."""
        user = InstagramUserFactory(
            username="testuser",
            full_name="Original Name",
            follower_count=100,
        )

        # Update follower count
        user.follower_count = 200
        user.save()

        # Update full name
        user.full_name = "New Name"
        user.save()

        url = reverse("instagram:user_history", kwargs={"uuid": user.uuid})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]

        # Most recent should have new values
        assert results[0]["full_name"] == "New Name"
        assert results[0]["follower_count"] == 200  # noqa: PLR2004

        # Second record should have old name, new follower count
        assert results[1]["full_name"] == "Original Name"
        assert results[1]["follower_count"] == 200  # noqa: PLR2004

        # Oldest record should have original values
        assert results[2]["full_name"] == "Original Name"
        assert results[2]["follower_count"] == 100  # noqa: PLR2004

    def test_history_empty_for_new_user(self):
        """Test that a newly created user has one history record (creation)."""
        user = InstagramUserFactory(username="newuser")

        url = reverse("instagram:user_history", kwargs={"uuid": user.uuid})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert len(results) == 1
        assert results[0]["history_type"] == "+"

    def test_history_multiple_users_isolation(self):
        """Test that history for one user doesn't include another user's history."""
        user1 = InstagramUserFactory(username="user1")
        user2 = InstagramUserFactory(username="user2")

        # Update both users
        user1.full_name = "User 1 Updated"
        user1.save()

        user2.full_name = "User 2 Updated"
        user2.save()

        # Get history for user1
        url1 = reverse("instagram:user_history", kwargs={"uuid": user1.uuid})
        response1 = self.client.get(url1)

        # Get history for user2
        url2 = reverse("instagram:user_history", kwargs={"uuid": user2.uuid})
        response2 = self.client.get(url2)

        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK

        # Each should have their own history
        results1 = response1.data["results"]
        results2 = response2.data["results"]

        assert all(r["username"] == "user1" for r in results1)
        assert all(r["username"] == "user2" for r in results2)
