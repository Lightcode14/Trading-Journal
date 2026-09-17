from rest_framework import serializers

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode

from trading.models import TradingAccount

from .models import (
    UserPreference,
)


User = get_user_model()


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
            "drawdown_warning_threshold",
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


    def validate_drawdown_warning_threshold(
        self,
        value,
    ):
        if value <= 0:
            raise serializers.ValidationError(
                "Drawdown warning threshold must be greater than 0%."
            )


        if value > 100:
            raise serializers.ValidationError(
                "Drawdown warning threshold cannot exceed 100%."
            )


        return value


class UserProfileSerializer(
    serializers.ModelSerializer
):

    display_name = serializers.CharField(
        required=False,
        allow_blank=True,
    )


    profile_photo = serializers.ImageField(
        required=False,
        allow_null=True,
    )


    class Meta:
        model = User

        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "display_name",
            "profile_photo",
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


    def validate_profile_photo(
        self,
        value,
    ):
        if value is None:
            return value


        maximum_size = (
            2 * 1024 * 1024
        )


        if value.size > maximum_size:
            raise serializers.ValidationError(
                "Profile photo must be 2MB or smaller."
            )


        content_type = getattr(
            value,
            "content_type",
            "",
        )


        allowed_types = (
            "image/jpeg",
            "image/png",
        )


        if (
            content_type and
            content_type not in allowed_types
        ):
            raise serializers.ValidationError(
                "Only JPG and PNG images are allowed."
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


class RegisterSerializer(
    serializers.ModelSerializer
):

    password = serializers.CharField(
        write_only=True,
        min_length=8,
    )


    password2 = serializers.CharField(
        write_only=True,
        min_length=8,
    )


    class Meta:
        model = User

        fields = (
            "id",
            "username",
            "email",
            "password",
            "password2",
        )

        read_only_fields = (
            "id",
        )


    # =========================================
    # EMAIL VALIDATION
    # =========================================

    def validate_email(
        self,
        value,
    ):
        value = value.strip().lower()


        if User.objects.filter(
            email__iexact=value
        ).exists():
            raise serializers.ValidationError(
                "An account with this email already exists."
            )


        return value


    # =========================================
    # PASSWORD VALIDATION
    # =========================================

    def validate(
        self,
        attrs,
    ):
        if (
            attrs["password"]
            != attrs["password2"]
        ):
            raise serializers.ValidationError(
                {
                    "password2":
                        "Passwords do not match."
                }
            )


        return attrs


    # =========================================
    # CREATE USER
    # =========================================

    def create(
        self,
        validated_data,
    ):
        validated_data.pop(
            "password2"
        )


        password = (
            validated_data.pop(
                "password"
            )
        )


        user = User.objects.create_user(
            password=password,
            **validated_data,
        )


        # Create default TradeCraft settings
        # automatically for the new user.
        UserPreference.objects.get_or_create(
            user=user
        )


        return user


class PasswordResetRequestSerializer(
    serializers.Serializer
):

    email = serializers.EmailField()


    def validate_email(
        self,
        value,
    ):
        return value.strip().lower()


class PasswordResetConfirmSerializer(
    serializers.Serializer
):

    uid = serializers.CharField()

    token = serializers.CharField()

    password = serializers.CharField(
        write_only=True,
        min_length=8,
    )

    password2 = serializers.CharField(
        write_only=True,
        min_length=8,
    )


    def validate(
        self,
        attrs,
    ):
        if (
            attrs["password"]
            != attrs["password2"]
        ):
            raise serializers.ValidationError(
                {
                    "password2":
                        "Passwords do not match."
                }
            )


        try:
            user_id = force_str(
                urlsafe_base64_decode(
                    attrs["uid"]
                )
            )


            user = User.objects.get(
                pk=user_id
            )


        except (
            User.DoesNotExist,
            ValueError,
            TypeError,
            OverflowError,
        ):
            raise serializers.ValidationError(
                {
                    "uid":
                        "Invalid password reset link."
                }
            )


        if not default_token_generator.check_token(
            user,
            attrs["token"],
        ):
            raise serializers.ValidationError(
                {
                    "token":
                        "Invalid or expired password reset token."
                }
            )


        attrs["user"] = user


        return attrs


    def save(
        self,
    ):
        user = self.validated_data[
            "user"
        ]


        user.set_password(
            self.validated_data[
                "password"
            ]
        )


        user.save(
            update_fields=[
                "password"
            ]
        )


        return user