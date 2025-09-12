from django.urls import path

from .views import ProcessInstagramDataView

app_name = "instagram"
urlpatterns = [
    path("inject-data/", ProcessInstagramDataView.as_view(), name="process_data"),
]
