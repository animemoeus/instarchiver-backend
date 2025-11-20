from django.urls import path

from instagram.views import InstagramUserDetailView
from instagram.views import InstagramUserHistoryView
from instagram.views import InstagramUserListView
from instagram.views import ProcessInstagramDataView
from instagram.views import StoryDetailView
from instagram.views import StoryListView

app_name = "instagram"
urlpatterns = [
    path("users/", InstagramUserListView.as_view(), name="user_list"),
    path("users/<uuid:uuid>/", InstagramUserDetailView.as_view(), name="user_detail"),
    path("stories/", StoryListView.as_view(), name="story_list"),
    path("stories/<str:story_id>/", StoryDetailView.as_view(), name="story_detail"),
    path(
        "users/<uuid:uuid>/history/",
        InstagramUserHistoryView.as_view(),
        name="user_history",
    ),
    path("inject-data/", ProcessInstagramDataView.as_view(), name="process_data"),
]
