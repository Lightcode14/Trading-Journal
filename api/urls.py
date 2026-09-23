from django.urls import path, include

from .views import health_check

from users.views import (
    TwoFactorDisableView,
    UserPreferenceView,
    UserProfileView,
    RegisterView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    TwoFactorStatusView,
    TwoFactorSetupView,
    TwoFactorEnableView,
    TwoFactorTokenView,
    TwoFactorVerifyLoginView,
)

from rest_framework_simplejwt.views import (
    TokenRefreshView,
)


urlpatterns = [

    path(
        "health/",
        health_check,
        name="health-check",
    ),

    path(
        "trading/",
        include("trading.urls"),
    ),

    # -------------------------
    # Authentication
    # -------------------------

    path(
        "token/",
        TwoFactorTokenView.as_view(),
        name="token_obtain_pair",
    ),

    path(
        "token-refresh/",
        TokenRefreshView.as_view(),
        name="token-refresh",
    ),

    # -------------------------
    # Two-Factor Authentication
    # -------------------------

    path(
        "2fa/status/",
        TwoFactorStatusView.as_view(),
        name="two-factor-status",
    ),

    path(
        "2fa/setup/",
        TwoFactorSetupView.as_view(),
        name="two-factor-setup",
    ),

    path(
        "2fa/enable/",
        TwoFactorEnableView.as_view(),
        name="two-factor-enable",
    ),

    path(
        "2fa/verify-login/",
        TwoFactorVerifyLoginView.as_view(),
        name="two-factor-verify-login",
    ),

    # -------------------------
    # User Settings / Profile
    # -------------------------

    path(
        "settings/",
        UserPreferenceView.as_view(),
        name="user-settings",
    ),

    path(
        "profile/",
        UserProfileView.as_view(),
        name="user-profile",
    ),

    # -------------------------
    # Registration
    # -------------------------

    path(
        "register/",
        RegisterView.as_view(),
        name="register",
    ),

    # -------------------------
    # Password Reset
    # -------------------------

    path(
        "password-reset/",
        PasswordResetRequestView.as_view(),
        name="password-reset",
    ),

    path(
        "password-reset-confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path(
    "2fa/disable/",
    TwoFactorDisableView.as_view(),
    name="two-factor-disable",
),
]