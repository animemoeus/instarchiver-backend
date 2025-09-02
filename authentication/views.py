import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from drf_spectacular.utils import OpenApiResponse
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from authentication import firebase

from .serializers import LoginWithGoogleSerializer
from .serializers import RefreshTokenSerializer

User = get_user_model()
logger = logging.getLogger(__name__)


class RefreshTokenView(APIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RefreshTokenSerializer

    @extend_schema(
        summary="Refresh JWT token",
        description="Refreshes the JWT token using the refresh token.",
        responses={
            200: OpenApiResponse(
                description="New JWT tokens",
            ),
        },
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        refresh = serializer.validated_data.get("refresh")
        try:
            token = RefreshToken(refresh)
        except Exception:  # noqa: BLE001
            return Response(
                {"error": "Invalid refresh token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "refresh": str(token),
                "access": str(token.access_token),
            },
        )


class ValidateTokenView(APIView):
    @extend_schema(
        summary="Validate JWT token",
        description="Validates the JWT token and returns user information.",
        responses={
            200: OpenApiResponse(),
        },
    )
    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return Response(
                {"error": "Invalid token"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return Response(
            {
                "detail": "Token is valid",
            },
            status=status.HTTP_200_OK,
        )


class LoginWithGoogleView(APIView):
    serializer_class = LoginWithGoogleSerializer
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        summary="Login with Google",
        description="Login a user using Google authentication.",
        request=LoginWithGoogleSerializer,
        responses={
            200: OpenApiResponse(
                description="User JWT tokens",
            ),
        },
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data.get("token")

        try:
            user_info = firebase.get_user_info(token)
        except Exception:
            logger.exception("Firebase authentication failed")
            return Response(
                {
                    "error": "Authentication failed",
                    "detail": "Invalid or expired token",
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        with transaction.atomic():
            user, created = User.objects.get_or_create(
                email=user_info.get("email"),
                defaults={
                    "username": user_info.get("email"),
                    "name": user_info.get("name", ""),
                    "photo_url": user_info.get("photo_url", ""),
                },
            )

            user.name = user_info.get("name", "")
            user.photo_url = user_info.get("photo_url", "")
            user.save()

            # Activate the user if they are not already active
            if not user.is_active:
                user.is_active = True
                user.save()

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
            status=status.HTTP_200_OK,
        )
