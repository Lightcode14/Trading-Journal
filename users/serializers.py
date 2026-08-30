from rest_framework import serializers

from trading.models import TradingAccount

from .models import UserPreference


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