from rest_framework.generics import (RetrieveUpdateAPIView,)
from rest_framework import (
    generics,
    permissions,
)
from rest_framework.permissions import (
    IsAuthenticated,
)
from django.conf import settings
from django.contrib.auth.tokens import (
    default_token_generator,
)
from django.core.mail import send_mail
from django.utils.encoding import (
    force_bytes,
)
from django.utils.http import (
    urlsafe_base64_encode,
)

from rest_framework import (
    permissions,
    status,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User

from .serializers import (
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
)

from users.models import (
    UserPreference,
)

from users.serializers import (
    UserPreferenceSerializer,
    UserProfileSerializer,
    RegisterSerializer
)


class UserPreferenceView(
    RetrieveUpdateAPIView
):
    serializer_class = (
        UserPreferenceSerializer
    )

    permission_classes = (
        IsAuthenticated,
    )


    def get_object(self):
        preferences, _ = (
            UserPreference.objects
            .get_or_create(
                user=self.request.user
            )
        )

        return preferences


class UserProfileView(
    RetrieveUpdateAPIView
):

    serializer_class = (
        UserProfileSerializer
    )

    permission_classes = (
        IsAuthenticated,
    )


    def get_object(self):
        return self.request.user

class RegisterView(
    generics.CreateAPIView
):
    serializer_class = (
        RegisterSerializer
    )

    permission_classes = [
        permissions.AllowAny
    ]

class PasswordResetRequestView(
    APIView
):
    permission_classes = [
        permissions.AllowAny
    ]


    def post(
        self,
        request,
    ):
        serializer = (
            PasswordResetRequestSerializer(
                data=request.data
            )
        )

        serializer.is_valid(
            raise_exception=True
        )

        email = serializer.validated_data[
            "email"
        ]


        user = User.objects.filter(
            email__iexact=email,
            is_active=True,
        ).first()


        # Always return the same response.
        # This prevents exposing whether
        # an email exists in the system.
        if user:
            uid = urlsafe_base64_encode(
                force_bytes(
                    user.pk
                )
            )

            token = (
                default_token_generator
                .make_token(
                    user
                )
            )


            reset_url = (
                f"http://localhost:5173/"
                f"reset-password"
                f"?uid={uid}"
                f"&token={token}"
            )
            


            send_mail(
                subject=(
                    "Reset your TradeCraft password"
                ),

                message=(
                    "Use the link below to reset "
                    "your TradeCraft password:\n\n"
                    f"{reset_url}"
                ),

                from_email=
                    settings.DEFAULT_FROM_EMAIL,

                recipient_list=[
                    user.email
                ],

                fail_silently=False,
            )


        return Response(
            {
                "detail":
                    "If an account exists with that email, a password reset link has been sent."
            },
            status=
                status.HTTP_200_OK,
        )


class PasswordResetConfirmView(
    APIView
):
    permission_classes = [
        permissions.AllowAny
    ]


    def post(
        self,
        request,
    ):
        serializer = (
            PasswordResetConfirmSerializer(
                data=request.data
            )
        )

        serializer.is_valid(
            raise_exception=True
        )

        serializer.save()


        return Response(
            {
                "detail":
                    "Password has been reset successfully."
            },
            status=
                status.HTTP_200_OK,
        )