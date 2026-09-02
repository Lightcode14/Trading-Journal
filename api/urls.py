from django.urls import path, include
from .views import health_check
from users.views import UserPreferenceView,UserProfileView
from rest_framework_simplejwt.views import TokenObtainPairView,TokenRefreshView
urlpatterns = [
    path('health/', health_check, name='health-check'),
    path('trading/', include('trading.urls')),
    path('auth-token/',TokenObtainPairView.as_view(), name='token-obtain'),
    path('token-refresh/',TokenRefreshView.as_view(), name='token-refresh'),
    path("settings/", UserPreferenceView.as_view(),name="user-settings"),
    path( "profile/",UserProfileView.as_view(),name="user-profile"),
]