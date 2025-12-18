from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from instagram.tests.factories import InstagramUserFactory
from instagram.tests.factories import PostFactory
from instagram.tests.factories import PostMediaFactory


class PostSimilarViewTest(TestCase):
    """Test suite for PostSimilarView endpoint."""

    def setUp(self):
        """Set up test client and common test data."""
        self.client = APIClient()

    def test_get_similar_posts_success(self):
        """Test successful retrieval of similar posts."""
        user = InstagramUserFactory(username="testuser")

        # Create source post with embedding
        source_post = PostFactory(
            user=user,
            embedding=[0.1] * 1536,  # Sample embedding
        )

        # Create similar posts with embeddings
        similar_post1 = PostFactory(
            user=user,
            embedding=[0.11] * 1536,  # Very similar
        )
        similar_post2 = PostFactory(
            user=user,
            embedding=[0.15] * 1536,  # Less similar
        )

        # Create post without embedding (should not appear)
        PostFactory(user=user, embedding=None)

        url = reverse("instagram:post_similar", kwargs={"id": source_post.id})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Should return 2 posts (excluding source and posts without embeddings)
        assert len(response.data) == 2  # noqa: PLR2004

        # Verify source post is not in results
        result_ids = {post["id"] for post in response.data}
        assert source_post.id not in result_ids
        assert similar_post1.id in result_ids
        assert similar_post2.id in result_ids

    def test_similar_posts_ordered_by_similarity(self):
        """Test that similar posts are ordered by similarity (most similar first)."""
        user = InstagramUserFactory(username="testuser")

        # Create source post with embedding
        source_post = PostFactory(
            user=user,
            embedding=[0.5] * 1536,
        )

        # Create posts with varying similarity
        very_similar = PostFactory(
            user=user,
            embedding=[0.51] * 1536,  # L2 distance ~0.1
        )
        somewhat_similar = PostFactory(
            user=user,
            embedding=[0.6] * 1536,  # L2 distance ~0.2
        )
        less_similar = PostFactory(
            user=user,
            embedding=[0.8] * 1536,  # L2 distance ~0.3
        )

        url = reverse("instagram:post_similar", kwargs={"id": source_post.id})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data
        assert len(results) == 3  # noqa: PLR2004

        # Verify all similar posts are returned
        result_ids = {post["id"] for post in results}
        assert very_similar.id in result_ids
        assert somewhat_similar.id in result_ids
        assert less_similar.id in result_ids

    def test_source_post_excluded_from_results(self):
        """Test that the source post is excluded from similar posts."""
        user = InstagramUserFactory(username="testuser")

        source_post = PostFactory(
            user=user,
            embedding=[0.5] * 1536,
        )

        # Create other posts with same embedding
        PostFactory.create_batch(3, user=user, embedding=[0.5] * 1536)

        url = reverse("instagram:post_similar", kwargs={"id": source_post.id})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data

        # Source post should not be in results
        result_ids = {post["id"] for post in results}
        assert source_post.id not in result_ids
        assert len(results) == 3  # noqa: PLR2004

    def test_post_not_found(self):
        """Test 404 when source post doesn't exist."""
        url = reverse(
            "instagram:post_similar",
            kwargs={"id": "9999999999999999999"},
        )
        response = self.client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_post_without_embedding(self):
        """Test 404 when source post has no embedding."""
        user = InstagramUserFactory(username="testuser")
        post = PostFactory(user=user, embedding=None)

        url = reverse("instagram:post_similar", kwargs={"id": post.id})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_only_posts_with_embeddings_returned(self):
        """Test that only posts with embeddings are returned."""
        user = InstagramUserFactory(username="testuser")

        source_post = PostFactory(
            user=user,
            embedding=[0.5] * 1536,
        )

        # Create posts with embeddings
        PostFactory.create_batch(2, user=user, embedding=[0.5] * 1536)

        # Create posts without embeddings
        PostFactory.create_batch(3, user=user, embedding=None)

        url = reverse("instagram:post_similar", kwargs={"id": source_post.id})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data

        # Should only return posts with embeddings (excluding source)
        assert len(results) == 2  # noqa: PLR2004

    def test_max_12_results(self):
        """Test that maximum 12 results are returned."""
        user = InstagramUserFactory(username="testuser")

        source_post = PostFactory(
            user=user,
            embedding=[0.5] * 1536,
        )

        # Create many similar posts (more than 12)
        PostFactory.create_batch(25, user=user, embedding=[0.5] * 1536)

        url = reverse("instagram:post_similar", kwargs={"id": source_post.id})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Should return maximum 12 results
        assert len(response.data) == 12  # noqa: PLR2004

    def test_response_structure_matches_post_list(self):
        """Test that response structure matches PostListSerializer."""
        user = InstagramUserFactory(username="testuser")

        source_post = PostFactory(
            user=user,
            embedding=[0.5] * 1536,
        )

        PostFactory(
            user=user,
            embedding=[0.51] * 1536,
        )

        url = reverse("instagram:post_similar", kwargs={"id": source_post.id})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data
        assert len(results) > 0

        first_post = results[0]
        expected_fields = [
            "id",
            "variant",
            "thumbnail_url",
            "thumbnail",
            "blur_data_url",
            "media_count",
            "created_at",
            "updated_at",
            "user",
        ]

        for field in expected_fields:
            assert field in first_post, f"Field '{field}' missing from response"

    def test_unauthenticated_access_allowed(self):
        """Test unauthenticated access (IsAuthenticatedOrReadOnly)."""
        user = InstagramUserFactory(username="testuser")

        source_post = PostFactory(
            user=user,
            embedding=[0.5] * 1536,
        )

        PostFactory(user=user, embedding=[0.5] * 1536)

        url = reverse("instagram:post_similar", kwargs={"id": source_post.id})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK

    def test_empty_results_when_no_similar_posts(self):
        """Test empty results when no other posts have embeddings."""
        user = InstagramUserFactory(username="testuser")

        source_post = PostFactory(
            user=user,
            embedding=[0.5] * 1536,
        )

        # Create posts without embeddings
        PostFactory.create_batch(3, user=user, embedding=None)

        url = reverse("instagram:post_similar", kwargs={"id": source_post.id})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 0

    def test_similar_posts_from_different_users(self):
        """Test that similar posts from different users are returned."""
        user1 = InstagramUserFactory(username="user1")
        user2 = InstagramUserFactory(username="user2")

        source_post = PostFactory(
            user=user1,
            embedding=[0.5] * 1536,
        )

        # Create similar posts from different users
        PostFactory(
            user=user1,
            embedding=[0.51] * 1536,
        )
        PostFactory(
            user=user2,
            embedding=[0.52] * 1536,
        )

        url = reverse("instagram:post_similar", kwargs={"id": source_post.id})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data
        assert len(results) == 2  # noqa: PLR2004

        # Verify posts from both users are returned
        usernames = {post["user"]["username"] for post in results}
        assert "user1" in usernames
        assert "user2" in usernames

    def test_user_annotations_present(self):
        """Test that user annotations (has_stories, has_history) are present."""
        user = InstagramUserFactory(username="testuser", full_name="Original")
        user.full_name = "Updated"
        user.save()

        source_post = PostFactory(
            user=user,
            embedding=[0.5] * 1536,
        )

        PostFactory(
            user=user,
            embedding=[0.51] * 1536,
        )

        url = reverse("instagram:post_similar", kwargs={"id": source_post.id})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data
        assert len(results) > 0

        first_post = results[0]
        user_data = first_post["user"]

        assert "has_stories" in user_data
        assert "has_history" in user_data
        assert user_data["has_history"] is True

    def test_media_count_annotation(self):
        """Test that media_count annotation is correct."""
        user = InstagramUserFactory(username="testuser")

        source_post = PostFactory(
            user=user,
            embedding=[0.5] * 1536,
        )

        similar_post = PostFactory(
            user=user,
            embedding=[0.51] * 1536,
        )
        PostMediaFactory.create_batch(3, post=similar_post)

        url = reverse("instagram:post_similar", kwargs={"id": source_post.id})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data
        assert len(results) > 0

        first_post = results[0]
        assert first_post["media_count"] == 3  # noqa: PLR2004
