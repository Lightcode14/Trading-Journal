from rest_framework.generics import (
    RetrieveUpdateAPIView,
)

from rest_framework.permissions import (
    IsAuthenticated,
)

from users.models import (
    UserPreference,
)

from users.serializers import (
    UserPreferenceSerializer,
    UserProfileSerializer
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