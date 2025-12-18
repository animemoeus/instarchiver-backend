from django.db.models import Count
from django.db.models import Exists
from django.db.models import OuterRef
from django.db.models import Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from pgvector.django import L2Distance
from rest_framework import filters
from rest_framework.generics import ListAPIView
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from core.utils.openai import generate_text_embedding
from instagram.models import Post
from instagram.models import PostMedia
from instagram.models import Story
from instagram.models import User as InstagramUser
from instagram.paginations import PostAISearchCursorPagination
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


class PostAISearchView(ListAPIView):
    """AI-powered semantic search endpoint for posts using embeddings."""

    serializer_class = PostListSerializer
    pagination_class = PostAISearchCursorPagination
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        # Get search query from request
        search_query = self.request.query_params.get("text", "").strip()

        if not search_query:
            # Return empty queryset if no search query provided
            return Post.objects.none()

        # Annotate users with has_stories and has_history
        annotated_users = InstagramUser.objects.annotate(
            has_stories=Exists(Story.objects.filter(user=OuterRef("pk"))),
            has_history=Exists(
                InstagramUser.history.model.objects.filter(uuid=OuterRef("pk")),
            ),
        )

        # Order PostMedia by reference to ensure consistent ordering
        ordered_postmedia = PostMedia.objects.order_by("-reference")

        # Generate embedding for search query
        query_embedding, _ = generate_text_embedding(search_query)

        # Filter posts with embeddings and order by similarity
        return (
            Post.objects.filter(embedding__isnull=False)
            .prefetch_related(
                Prefetch("user", queryset=annotated_users),
                Prefetch("postmedia_set", queryset=ordered_postmedia),
            )
            .annotate(
                media_count=Count("postmedia"),
                similarity_score=1 - L2Distance("embedding", query_embedding),
            )
            .order_by("-similarity_score")
        )

    def get(self, request, *args, **kwargs):
        if not self.request.query_params.get("text"):
            return Response(
                {"error": "Text parameter is required"},
                status=400,
            )

        return super().get(request, *args, **kwargs)
