from django.db.models import Count
from django.db.models import Exists
from django.db.models import OuterRef
from django.db.models import Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from pgvector.django import L2Distance
from rest_framework import filters
from rest_framework.exceptions import NotFound
from rest_framework.generics import ListAPIView
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from instagram.models import Post
from instagram.models import PostMedia
from instagram.models import Story
from instagram.models import User as InstagramUser
from instagram.paginations import PostCursorPagination
from instagram.serializers.posts import PostDetailSerializer
from instagram.serializers.posts import PostListSerializer


class PostListView(ListAPIView):
    queryset = Post.objects.all().order_by("-created_at")
    serializer_class = PostListSerializer
    pagination_class = PostCursorPagination
    permission_classes = [IsAuthenticatedOrReadOnly]

    filter_backends = [
        filters.SearchFilter,
        DjangoFilterBackend,
        filters.OrderingFilter,
    ]
    search_fields = ["user__username", "user__full_name", "user__biography", "caption"]
    filterset_fields = ["user", "variant"]
    ordering_fields = ["created_at", "updated_at", "post_created_at"]
    ordering = "-post_created_at"

    def get_queryset(self):
        # Annotate users with has_stories and has_history
        annotated_users = InstagramUser.objects.annotate(
            has_stories=Exists(Story.objects.filter(user=OuterRef("pk"))),
            has_history=Exists(
                InstagramUser.history.model.objects.filter(uuid=OuterRef("pk")),
            ),
        )

        # Order PostMedia by reference to ensure consistent ordering
        ordered_postmedia = PostMedia.objects.order_by("-reference")

        return (
            Post.objects.all()
            .prefetch_related(
                Prefetch("user", queryset=annotated_users),
                Prefetch("postmedia_set", queryset=ordered_postmedia),
            )
            .annotate(media_count=Count("postmedia"))
            .order_by("-created_at")
        )


class PostDetailView(RetrieveAPIView):
    queryset = Post.objects.all()
    serializer_class = PostDetailSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    lookup_field = "id"

    def get_queryset(self):
        # Annotate users with has_stories and has_history
        annotated_users = InstagramUser.objects.annotate(
            has_stories=Exists(Story.objects.filter(user=OuterRef("pk"))),
            has_history=Exists(
                InstagramUser.history.model.objects.filter(uuid=OuterRef("pk")),
            ),
        )

        # Order PostMedia by created_at to ensure consistent ordering
        ordered_postmedia = PostMedia.objects.order_by("-reference")

        return Post.objects.all().prefetch_related(
            Prefetch("user", queryset=annotated_users),
            Prefetch("postmedia_set", queryset=ordered_postmedia),
        )


class PostSimilarView(ListAPIView):
    """
    API endpoint to retrieve similar posts based on embedding similarity.

    Uses pgvector's L2Distance to find semantically similar posts to a given post.
    Returns up to 12 similar posts ordered by similarity (most similar first).
    """

    serializer_class = PostListSerializer
    pagination_class = None  # Disable pagination
    permission_classes = [IsAuthenticatedOrReadOnly]
    lookup_field = "id"

    @extend_schema(
        summary="Get similar posts",
        description=(
            "Retrieve up to 12 posts similar to the specified post based on "
            "embedding similarity. Uses pgvector's L2Distance to calculate "
            "semantic similarity between post embeddings. Returns posts "
            "ordered by similarity (most similar first). Only returns posts "
            "that have embeddings. The source post is excluded from results. "
            "Results are returned as a simple list without pagination."
        ),
        responses={
            200: PostListSerializer(many=True),
            404: {"description": "Post not found or post has no embedding"},
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        # Get the source post ID from URL
        post_id = self.kwargs.get("id")

        # Retrieve the source post
        try:
            source_post = Post.objects.get(id=post_id)
        except Post.DoesNotExist as exc:
            msg = f"Post with id '{post_id}' not found."
            raise NotFound(msg) from exc

        # Check if source post has an embedding
        if source_post.embedding is None:
            msg = f"Post with id '{post_id}' does not have an embedding."
            raise NotFound(msg)

        # Annotate users with has_stories and has_history
        annotated_users = InstagramUser.objects.annotate(
            has_stories=Exists(Story.objects.filter(user=OuterRef("pk"))),
            has_history=Exists(
                InstagramUser.history.model.objects.filter(uuid=OuterRef("pk")),
            ),
        )

        # Order PostMedia by reference to ensure consistent ordering
        ordered_postmedia = PostMedia.objects.order_by("-reference")

        # Query similar posts using L2Distance
        return (
            Post.objects.filter(embedding__isnull=False)
            .exclude(id=post_id)
            .prefetch_related(
                Prefetch("user", queryset=annotated_users),
                Prefetch("postmedia_set", queryset=ordered_postmedia),
            )
            .annotate(
                media_count=Count("postmedia"),
                similarity_score=L2Distance("embedding", source_post.embedding),
            )
            .order_by("similarity_score")[:12]  # Limit to 12 results
        )
