from django.db import models
from django.conf import settings
from users.models import User
import secrets


class TradingAccount(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="trading_accounts",
    )

    name = models.CharField(max_length=100)

    broker = models.CharField(
        max_length=100,
        blank=True,
    )

    account_number = models.CharField(
        max_length=100,
        blank=True,
    )

    currency = models.CharField(
        max_length=10,
        default="USD",
    )

    starting_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
    )

    webhook_secret = models.CharField(
        max_length=64,
        unique=True,
        blank=True,
        null=True,
    )

    webhook_enabled = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.webhook_secret:
            self.webhook_secret = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)


class Strategy(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="strategies",
    )

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Trade(models.Model):

    class Direction(models.TextChoices):
        LONG = "LONG", "Long"
        SHORT = "SHORT", "Short"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        CLOSED = "CLOSED", "Closed"

    class Source(models.TextChoices):
        MANUAL = "MANUAL", "Manual"
        TRADINGVIEW = "TRADINGVIEW", "TradingView"
        BROKER = "BROKER", "Broker"
        IMPORT = "IMPORT", "Import"

    class MarketType(models.TextChoices):
        FOREX = "FOREX", "Forex"
        CRYPTO = "CRYPTO", "Crypto"
        STOCK = "STOCK", "Stock"
        FUTURES = "FUTURES", "Futures"
        OTHER = "OTHER", "Other"

    class PositionSizeUnit(models.TextChoices):
        UNIT = "UNIT", "Units"
        STANDARD_LOT = "STANDARD_LOT", "Standard Lots"
        MINI_LOT = "MINI_LOT", "Mini Lots"
        MICRO_LOT = "MICRO_LOT", "Micro Lots"
        SHARE = "SHARE", "Shares"
        CONTRACT = "CONTRACT", "Contracts"

    account = models.ForeignKey(
        TradingAccount,
        on_delete=models.CASCADE,
        related_name="trades",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="trades",
    )

    strategy = models.ForeignKey(
        Strategy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="trades",
    )

    symbol = models.CharField(max_length=50)

    market_type = models.CharField(
        max_length=20,
        choices=MarketType.choices,
        default=MarketType.OTHER,
    )

    direction = models.CharField(
        max_length=10,
        choices=Direction.choices,
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.CLOSED,
    )

    entry_price = models.DecimalField(
        max_digits=20,
        decimal_places=8,
    )

    exit_price = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        null=True,
        blank=True,
    )

    stop_loss = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        null=True,
        blank=True,
    )

    take_profit = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        null=True,
        blank=True,
    )

    position_size = models.DecimalField(
        max_digits=20,
        decimal_places=8,
    )

    position_size_unit = models.CharField(
        max_length=20,
        choices=PositionSizeUnit.choices,
        default=PositionSizeUnit.UNIT,
    )

    risk_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
    )

    risk_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )

    profit_loss = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
    )

    fees = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
    )

    entry_time = models.DateTimeField()

    exit_time = models.DateTimeField(
        null=True,
        blank=True,
    )

    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.MANUAL,
    )

    external_trade_id = models.CharField(
        max_length=255,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "account",
                    "source",
                    "external_trade_id",
                ],
                condition=~models.Q(external_trade_id=""),
                name="unique_external_trade_per_account_source",
            )
        ]

    def __str__(self):
        return f"{self.symbol} - {self.direction}"


class JournalEntry(models.Model):
    trade = models.OneToOneField(
        Trade,
        on_delete=models.CASCADE,
        related_name="journal",
    )

    pre_trade_analysis = models.TextField(blank=True)
    entry_reason = models.TextField(blank=True)
    market_analysis = models.TextField(blank=True)
    emotions = models.TextField(blank=True)
    exit_reason = models.TextField(blank=True)
    mistakes = models.TextField(blank=True)
    lessons = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Journal - {self.trade}"


class Goal(models.Model):

    class GoalType(models.TextChoices):
        PROFIT = "PROFIT", "Profit Target"
        TRADE_COUNT = "TRADE_COUNT", "Trade Count"
        WIN_RATE = "WIN_RATE", "Win Rate"
        JOURNAL_COMPLETION = "JOURNAL_COMPLETION", "Journal Completion"
        MAX_LOSS = "MAX_LOSS", "Maximum Loss"
        AVERAGE_RISK = "AVERAGE_RISK", "Average Risk"

    class Period(models.TextChoices):
        DAILY = "DAILY", "Daily"
        WEEKLY = "WEEKLY", "Weekly"
        MONTHLY = "MONTHLY", "Monthly"
        QUARTERLY = "QUARTERLY", "Quarterly"
        YEARLY = "YEARLY", "Yearly"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        COMPLETED = "COMPLETED", "Completed"
        PAUSED = "PAUSED", "Paused"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="goals",
    )

    account = models.ForeignKey(
        "trading.TradingAccount",
        on_delete=models.CASCADE,
        related_name="goals",
        null=True,
        blank=True,
    )

    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    goal_type = models.CharField(
        max_length=30,
        choices=GoalType.choices,
    )

    target = models.DecimalField(
        max_digits=15,
        decimal_places=2,
    )

    period = models.CharField(
        max_length=20,
        choices=Period.choices,
        default=Period.MONTHLY,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} - {self.title}"
class Notification(models.Model):

    class Type(models.TextChoices):
        GOAL_REACHED = (
            "GOAL_REACHED",
            "Goal Reached",
        )

        DRAWDOWN_WARNING = (
            "DRAWDOWN_WARNING",
            "Drawdown Warning",
        )

        JOURNAL_REMINDER = (
            "JOURNAL_REMINDER",
            "Journal Reminder",
        )

        WEEKLY_SUMMARY = (
            "WEEKLY_SUMMARY",
            "Weekly Summary",
        )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    notification_type = models.CharField(
        max_length=30,
        choices=Type.choices,
    )

    title = models.CharField(
        max_length=150,
    )

    message = models.TextField()

    is_read = models.BooleanField(
        default=False,
    )

    goal = models.ForeignKey(
        Goal,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )

    event_key = models.CharField(
        max_length=100,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "-created_at",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "user",
                    "notification_type",
                    "goal",
                    "event_key",
                ],
                condition=models.Q(
                    goal__isnull=False
                ),
                name=(
                    "unique_goal_notification_event"
                ),
            )
        ]

    def __str__(self):
        return (
            f"{self.user} - "
            f"{self.title}"
        )