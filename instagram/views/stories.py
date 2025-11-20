from django.db.models import Exists
from django.db.models import OuterRef
from django.db.models import Prefetch
from rest_framework.generics import ListAPIView
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from instagram.models import Story
from instagram.models import User as InstagramUser
from instagram.paginations import StoryCursorPagination
from instagram.serializers.stories import StoryDetailSerializer
from instagram.serializers.stories import StoryListSerializer


class StoryListView(ListAPIView):
    queryset = Story.objects.all().order_by("-created_at")
    serializer_class = StoryListSerializer
    pagination_class = StoryCursorPagination
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        # Annotate users with has_stories and has_history
        annotated_users = InstagramUser.objects.annotate(
            has_stories=Exists(Story.objects.filter(user=OuterRef("pk"))),
            has_history=Exists(
                InstagramUser.history.model.objects.filter(uuid=OuterRef("pk")),
            ),
        )

        return (
            Story.objects.all()
            .prefetch_related(
                Prefetch("user", queryset=annotated_users),
            )
            .order_by("-created_at")
        )


class StoryDetailView(RetrieveAPIView):
    queryset = Story.objects.all()
    serializer_class = StoryDetailSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    lookup_field = "story_id"

    def get_queryset(self):
        # Annotate users with has_stories and has_history
        annotated_users = InstagramUser.objects.annotate(
            has_stories=Exists(Story.objects.filter(user=OuterRef("pk"))),
            has_history=Exists(
                InstagramUser.history.model.objects.filter(uuid=OuterRef("pk")),
            ),
        )

        return Story.objects.all().prefetch_related(
            Prefetch("user", queryset=annotated_users),
        )
