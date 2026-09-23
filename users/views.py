from rest_framework.generics import (
    RetrieveUpdateAPIView,
)

import pyotp

from rest_framework import (
    generics,
    permissions,
    status,
)

from rest_framework.permissions import (
    IsAuthenticated,
)

from rest_framework.parsers import (
    MultiPartParser,
    FormParser,
    JSONParser,
)

from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework_simplejwt.tokens import (
    RefreshToken,
)

from django.conf import settings

from django.contrib.auth import (
    authenticate,
)

from django.contrib.auth.tokens import (
    default_token_generator,
)

from django.core import signing

from django.core.mail import send_mail

from django.utils.encoding import (
    force_bytes,
)

from django.utils.http import (
    urlsafe_base64_encode,
)


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
    RegisterSerializer,
)


TWO_FACTOR_CHALLENGE_SALT = (
    "tradecraft.two-factor-login"
)

TWO_FACTOR_CHALLENGE_MAX_AGE = 300


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

    parser_classes = (
        MultiPartParser,
        FormParser,
        JSONParser,
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

            uid = (
                urlsafe_base64_encode(
                    force_bytes(
                        user.pk
                    )
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


class TwoFactorStatusView(
    APIView
):

    permission_classes = [
        IsAuthenticated
    ]


    def get(
        self,
        request,
    ):

        return Response(
            {
                "enabled":
                    request.user.two_factor_enabled
            },
            status=status.HTTP_200_OK,
        )


class TwoFactorSetupView(
    APIView
):

    permission_classes = [
        IsAuthenticated
    ]


    def post(
        self,
        request,
    ):

        user = request.user

        if user.two_factor_enabled:

            return Response(
                {
                    "detail":
                        "Two-factor authentication is already enabled."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        secret = pyotp.random_base32()

        user.two_factor_secret = secret

        user.save(
            update_fields=[
                "two_factor_secret"
            ]
        )

        provisioning_uri = (
            pyotp.TOTP(secret)
            .provisioning_uri(
                name=user.email or user.username,
                issuer_name="TradeCraft",
            )
        )

        return Response(
            {
                "secret": secret,
                "provisioning_uri":
                    provisioning_uri,
            },
            status=status.HTTP_200_OK,
        )


class TwoFactorEnableView(
    APIView
):

    permission_classes = [
        IsAuthenticated
    ]


    def post(
        self,
        request,
    ):

        user = request.user

        if user.two_factor_enabled:

            return Response(
                {
                    "detail":
                        "Two-factor authentication is already enabled."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        secret = (
            user.two_factor_secret
        )

        if not secret:

            return Response(
                {
                    "detail":
                        "Two-factor authentication setup has not been started."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        code = str(
            request.data.get(
                "code",
                "",
            )
        ).strip()

        if not code:

            return Response(
                {
                    "code":
                        "Enter the 6-digit authentication code."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        totp = pyotp.TOTP(
            secret
        )

        is_valid = totp.verify(
            code,
            valid_window=1,
        )

        if not is_valid:

            return Response(
                {
                    "code":
                        "Invalid or expired authentication code."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.two_factor_enabled = True

        user.save(
            update_fields=[
                "two_factor_enabled"
            ]
        )

        return Response(
            {
                "detail":
                    "Two-factor authentication has been enabled successfully.",

                "enabled":
                    True,
            },
            status=status.HTTP_200_OK,
        )


class TwoFactorTokenView(
    APIView
):

    permission_classes = [
        permissions.AllowAny
    ]

    authentication_classes = []


    def post(
        self,
        request,
    ):

        username = str(
            request.data.get(
                "username",
                "",
            )
        ).strip()

        password = str(
            request.data.get(
                "password",
                "",
            )
        )

        if not username or not password:

            return Response(
                {
                    "detail":
                        "Username and password are required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(
            request=request,
            username=username,
            password=password,
        )

        if (
            user is None
            or not user.is_active
        ):

            return Response(
                {
                    "detail":
                        "No active account found with the given credentials"
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if user.two_factor_enabled:

            challenge = signing.dumps(
                {
                    "user_id": user.pk,
                    "purpose":
                        "two_factor_login",
                },
                salt=
                    TWO_FACTOR_CHALLENGE_SALT,
            )

            return Response(
                {
                    "two_factor_required":
                        True,

                    "challenge":
                        challenge,
                },
                status=status.HTTP_200_OK,
            )

        refresh = RefreshToken.for_user(
            user
        )

        return Response(
            {
                "refresh":
                    str(refresh),

                "access":
                    str(
                        refresh.access_token
                    ),
            },
            status=status.HTTP_200_OK,
        )


class TwoFactorVerifyLoginView(
    APIView
):

    permission_classes = [
        permissions.AllowAny
    ]

    authentication_classes = []


    def post(
        self,
        request,
    ):

        challenge = str(
            request.data.get(
                "challenge",
                "",
            )
        ).strip()

        code = str(
            request.data.get(
                "code",
                "",
            )
        ).strip()

        if not challenge or not code:

            return Response(
                {
                    "detail":
                        "Challenge and authentication code are required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:

            challenge_data = (
                signing.loads(
                    challenge,
                    salt=
                        TWO_FACTOR_CHALLENGE_SALT,
                    max_age=
                        TWO_FACTOR_CHALLENGE_MAX_AGE,
                )
            )

        except signing.SignatureExpired:

            return Response(
                {
                    "detail":
                        "The two-factor authentication challenge has expired. Please log in again."
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        except signing.BadSignature:

            return Response(
                {
                    "detail":
                        "Invalid two-factor authentication challenge."
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if (
            challenge_data.get(
                "purpose"
            )
            != "two_factor_login"
        ):

            return Response(
                {
                    "detail":
                        "Invalid two-factor authentication challenge."
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user = User.objects.filter(
            pk=challenge_data.get(
                "user_id"
            ),
            is_active=True,
        ).first()

        if user is None:

            return Response(
                {
                    "detail":
                        "Unable to verify this login."
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if (
            not user.two_factor_enabled
            or not user.two_factor_secret
        ):

            return Response(
                {
                    "detail":
                        "Two-factor authentication is not enabled for this account."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        totp = pyotp.TOTP(
            user.two_factor_secret
        )

        if not totp.verify(
            code,
            valid_window=1,
        ):

            return Response(
                {
                    "code":
                        "Invalid or expired authentication code."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        refresh = RefreshToken.for_user(
            user
        )

        return Response(
            {
                "refresh":
                    str(refresh),

                "access":
                    str(
                        refresh.access_token
                    ),
            },
            status=status.HTTP_200_OK,
        )
class TwoFactorDisableView(
    APIView
):

    permission_classes = [
        IsAuthenticated
    ]


    def post(
        self,
        request,
    ):

        user = request.user

        if not user.two_factor_enabled:

            return Response(
                {
                    "detail":
                        "Two-factor authentication is not enabled."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        password = str(
            request.data.get(
                "password",
                "",
            )
        )

        code = str(
            request.data.get(
                "code",
                "",
            )
        ).strip()

        if not password:

            return Response(
                {
                    "password":
                        "Enter your current password."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not code:

            return Response(
                {
                    "code":
                        "Enter the 6-digit authentication code."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user.check_password(
            password
        ):

            return Response(
                {
                    "password":
                        "Incorrect password."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user.two_factor_secret:

            return Response(
                {
                    "detail":
                        "Two-factor authentication configuration is invalid."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        totp = pyotp.TOTP(
            user.two_factor_secret
        )

        if not totp.verify(
            code,
            valid_window=1,
        ):

            return Response(
                {
                    "code":
                        "Invalid or expired authentication code."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.two_factor_enabled = False
        user.two_factor_secret = ""

        user.save(
            update_fields=[
                "two_factor_enabled",
                "two_factor_secret",
            ]
        )

        return Response(
            {
                "detail":
                    "Two-factor authentication has been disabled successfully.",

                "enabled":
                    False,
            },
            status=status.HTTP_200_OK,
        )