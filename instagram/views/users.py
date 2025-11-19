from django.db.models import Exists
from django.db.models import OuterRef
from rest_framework import filters
from rest_framework.generics import ListAPIView
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from instagram.models import Story
from instagram.models import User as InstagramUser
from instagram.paginations import InstagramUserCursorPagination
from instagram.serializers.users import InstagramUserDetailSerializer
from instagram.serializers.users import InstagramUserListSerializer


class InstagramUserListView(ListAPIView):
    queryset = InstagramUser.objects.all().order_by("-created_at")
    serializer_class = InstagramUserListSerializer
    pagination_class = InstagramUserCursorPagination
    permission_classes = [IsAuthenticatedOrReadOnly]

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["username", "full_name", "biography"]
    ordering_fields = ["created_at", "updated_at", "username", "full_name"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return (
            InstagramUser.objects.all()
            .prefetch_related("story_set")
            .annotate(
                has_stories=Exists(Story.objects.filter(user=OuterRef("pk"))),
                has_history=Exists(
                    InstagramUser.history.model.objects.filter(uuid=OuterRef("pk")),
                ),
            )
        )


class InstagramUserDetailView(RetrieveAPIView):
    queryset = InstagramUser.objects.all()
    serializer_class = InstagramUserDetailSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    lookup_field = "uuid"

    def get_queryset(self):
        return (
            InstagramUser.objects.all()
            .prefetch_related("story_set")
            .annotate(
                has_stories=Exists(Story.objects.filter(user=OuterRef("pk"))),
                has_history=Exists(
                    InstagramUser.history.model.objects.filter(uuid=OuterRef("pk")),
                ),
            )
        )
