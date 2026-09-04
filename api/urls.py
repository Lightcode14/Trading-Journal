from django.urls import path, include
from .views import health_check
from users.views import (
    UserPreferenceView,UserProfileView,RegisterView,
     PasswordResetConfirmView,
        PasswordResetRequestView,)
from rest_framework_simplejwt.views import TokenObtainPairView,TokenRefreshView



urlpatterns = [
    path('health/', health_check, name='health-check'),
    path('trading/', include('trading.urls')),
    path('token/',TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token-refresh/',TokenRefreshView.as_view(), name='token-refresh'),
    path("settings/", UserPreferenceView.as_view(),name="user-settings"),
    path( "profile/",UserProfileView.as_view(),name="user-profile"),
    path("register/",RegisterView.as_view(),name="register"),
    path("password-reset/",PasswordResetRequestView.as_view(), name="password-reset",),
    path("password-reset-confirm/",PasswordResetConfirmView.as_view(),name="password-reset-confirm",),
]