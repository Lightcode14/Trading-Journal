from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings


class User(AbstractUser):

    profile_photo = models.ImageField(
        upload_to="profile_photos/",
        null=True,
        blank=True,
    )


class UserPreference(models.Model):

    class RiskUnit(models.TextChoices):

        PERCENTAGE = (
            "PERCENTAGE",
            "Percentage",
        )

        FIXED = (
            "FIXED",
            "Fixed Amount",
        )


    class TradeStatus(models.TextChoices):

        OPEN = "OPEN", "Open"

        CLOSED = "CLOSED", "Closed"


    class Currency(models.TextChoices):

        USD = "USD", "USD"

        EUR = "EUR", "EUR"

        GBP = "GBP", "GBP"

        NGN = "NGN", "NGN"


    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="preferences",
    )


    # ============================
    # TRADING PREFERENCES
    # ============================

    default_currency = models.CharField(
        max_length=10,
        choices=Currency.choices,
        default=Currency.USD,
    )


    default_account = models.ForeignKey(
        "trading.TradingAccount",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="default_for_users",
    )


    display_name = models.CharField(
        max_length=100,
        blank=True,
    )


    default_risk_unit = models.CharField(
        max_length=20,
        choices=RiskUnit.choices,
        default=RiskUnit.PERCENTAGE,
    )


    default_risk_per_trade = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1,
    )


    auto_calculate_r = models.BooleanField(
        default=True
    )


    include_fees = models.BooleanField(
        default=True
    )


    default_trade_status = models.CharField(
        max_length=10,
        choices=TradeStatus.choices,
        default=TradeStatus.OPEN,
    )


    # ============================
    # NOTIFICATIONS
    # ============================

    goal_alerts = models.BooleanField(
        default=True
    )


    drawdown_warnings = models.BooleanField(
        default=True
    )


    drawdown_warning_threshold = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10,
    )


    journal_reminders = models.BooleanField(
        default=True
    )


    weekly_summary = models.BooleanField(
        default=False
    )


    created_at = models.DateTimeField(
        auto_now_add=True
    )


    updated_at = models.DateTimeField(
        auto_now=True
    )


    def __str__(self):

        return (
            f"{self.user} preferences"
        )