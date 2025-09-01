from django.urls import path

from .views import LoginWithGoogleView
from .views import RefreshTokenView
from .views import ValidateTokenView

app_name = "authentication"

urlpatterns = [
    path("login-with-google/", LoginWithGoogleView.as_view(), name="google-login"),
    path("refresh/", RefreshTokenView.as_view(), name="refresh-token"),
    path("validate/", ValidateTokenView.as_view(), name="validate-token"),
]
