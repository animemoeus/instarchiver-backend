from django.urls import path

from instagram.views import InstagramUserListView
from instagram.views import ProcessInstagramDataView

app_name = "instagram"
urlpatterns = [
    path("users/", InstagramUserListView.as_view(), name="user_list"),
    path("inject-data/", ProcessInstagramDataView.as_view(), name="process_data"),
]
