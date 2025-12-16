from django.db.models import Count
from django.db.models import Exists
from django.db.models import OuterRef
from django.db.models import Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
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
    search_fields = ["user__username", "user__full_name", "user__biography"]
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
