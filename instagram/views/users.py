from django.db import transaction
from django.db.models import Exists
from django.db.models import OuterRef
from rest_framework import filters
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.generics import ListCreateAPIView
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from instagram.models import Story
from instagram.models import User as InstagramUser
from instagram.paginations import InstagramUserCursorPagination
from instagram.paginations import InstagramUserHistoryCursorPagination
from instagram.serializers.users import InstagramUserCreateSerializer
from instagram.serializers.users import InstagramUserDetailSerializer
from instagram.serializers.users import InstagramUserHistoryListSerializer
from instagram.serializers.users import InstagramUserListSerializer


class InstagramUserListCreateView(ListCreateAPIView):
    queryset = InstagramUser.objects.all().order_by("-created_at")
    serializer_class = InstagramUserListSerializer
    pagination_class = InstagramUserCursorPagination
    permission_classes = [IsAuthenticatedOrReadOnly]

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["username", "full_name", "biography"]
    ordering_fields = ["created_at", "updated_at", "username", "full_name"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        """Use different serializers for list and create actions."""
        if self.request.method == "POST":
            return InstagramUserCreateSerializer
        return InstagramUserListSerializer

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

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                serializer.save()
        except Exception as e:  # noqa: BLE001
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Use user detail serializer to return the created user
        serializer = InstagramUserDetailSerializer(serializer.instance)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class InstagramUserDetailView(RetrieveAPIView):
    queryset = InstagramUser.objects.all()
    serializer_class = InstagramUserDetailSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    lookup_field = "uuid"
    filter_backends = [filters.SearchFilter]
    search_fields = ["full_name", "username", "biography"]

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


class InstagramUserHistoryView(ListAPIView):
    serializer_class = InstagramUserHistoryListSerializer
    pagination_class = InstagramUserHistoryCursorPagination
    permission_classes = [IsAuthenticatedOrReadOnly]
    lookup_field = "uuid"

    def get_queryset(self):
        uuid = self.kwargs.get("uuid")
        return InstagramUser.history.filter(uuid=uuid).order_by("-history_date")
