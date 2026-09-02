from rest_framework import serializers

from trading.models import TradingAccount

from .models import UserPreference,User


class UserPreferenceSerializer(
    serializers.ModelSerializer
):

    default_account = (
        serializers.PrimaryKeyRelatedField(
            queryset=TradingAccount.objects.all(),
            required=False,
            allow_null=True,
        )
    )


    class Meta:
        model = UserPreference

        fields = (
            "default_currency",
            "default_account",
            "default_risk_unit",
            "default_risk_per_trade",
            "auto_calculate_r",
            "include_fees",
            "default_trade_status",
            "goal_alerts",
            "drawdown_warnings",
            "journal_reminders",
            "weekly_summary",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "created_at",
            "updated_at",
        )


    def validate_default_account(
        self,
        account,
    ):
        if account is None:
            return account


        request = self.context.get(
            "request"
        )


        if (
            request and
            account.user != request.user
        ):
            raise serializers.ValidationError(
                "You cannot use another user's account as your default account."
            )


        return account


    def validate_default_risk_per_trade(
        self,
        value,
    ):
        if value < 0:
            raise serializers.ValidationError(
                "Default risk cannot be negative."
            )


        return value


from rest_framework import serializers

from .models import (
    User,
    UserPreference,
)


class UserProfileSerializer(
    serializers.ModelSerializer
):
    display_name = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    class Meta:
        model = User

        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "display_name",
        )

        read_only_fields = (
            "id",
        )


    def validate_email(
        self,
        value,
    ):
        value = value.lower().strip()

        queryset = (
            User.objects
            .filter(
                email__iexact=value
            )
        )

        if self.instance:
            queryset = queryset.exclude(
                pk=self.instance.pk
            )

        if queryset.exists():
            raise serializers.ValidationError(
                "A user with this email address already exists."
            )

        return value


    def to_representation(
        self,
        instance,
    ):
        data = super().to_representation(
            instance
        )

        preferences = getattr(
            instance,
            "preferences",
            None,
        )

        data["display_name"] = (
            preferences.display_name
            if preferences
            else ""
        )

        return data


    def update(
        self,
        instance,
        validated_data,
    ):
        display_name = (
            validated_data.pop(
                "display_name",
                None,
            )
        )

        instance = super().update(
            instance,
            validated_data,
        )

        preferences, _ = (
            UserPreference.objects
            .get_or_create(
                user=instance
            )
        )

        if display_name is not None:
            preferences.display_name = (
                display_name
            )

            preferences.save(
                update_fields=[
                    "display_name",
                    "updated_at",
                ]
            )

        return instance