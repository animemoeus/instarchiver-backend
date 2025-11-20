from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from instagram.models import Story
from instagram.paginations import StoryCursorPagination
from instagram.serializers.stories import StoryListSerializer


class StoryListView(ListAPIView):
    queryset = Story.objects.all().order_by("-created_at")
    serializer_class = StoryListSerializer
    pagination_class = StoryCursorPagination
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        return Story.objects.all().select_related("user").order_by("-created_at")
