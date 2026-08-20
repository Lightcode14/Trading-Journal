from django.db import models
from django.conf import settings
from users.models import User

class TradingAccount(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='trading_accounts'
    )
    name = models.CharField(max_length=100)
    broker = models.CharField(max_length=100,blank=True)
    account_identifier = models.CharField( max_length=100, blank=True)
    currency = models.CharField( max_length=10,default='USD')
    starting_balance = models.DecimalField(max_digits=15,decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
class Strategy(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='strategies'
    )

    name = models.CharField(max_length=100)

    description = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.name

class Trade(models.Model):

    class Direction(models.TextChoices):
        LONG = 'LONG', 'Long'
        SHORT = 'SHORT', 'Short'

    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        CLOSED = 'CLOSED', 'Closed'

    class Source(models.TextChoices):
        MANUAL = 'MANUAL', 'Manual'
        TRADINGVIEW = 'TRADINGVIEW', 'TradingView'
        BROKER = 'BROKER', 'Broker'
        IMPORT = 'IMPORT', 'Import'

    account = models.ForeignKey(
        TradingAccount,
        on_delete=models.CASCADE,
        related_name='trades'
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='trades'
    )

    strategy = models.ForeignKey(
        Strategy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='trades'
    )

    direction = models.CharField(
        max_length=10,
        choices=Direction.choices
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.CLOSED
    )

    entry_price = models.DecimalField(
        max_digits=20,
        decimal_places=8
    )

    exit_price = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        null=True,
        blank=True
    )

    stop_loss = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        null=True,
        blank=True
    )

    take_profit = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        null=True,
        blank=True
    )

    position_size = models.DecimalField(
        max_digits=20,
        decimal_places=8
    )

    risk_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )

    profit_loss = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )

    fees = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )

    entry_time = models.DateTimeField()

    exit_time = models.DateTimeField(
        null=True,
        blank=True
    )

    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.MANUAL
    )

    external_trade_id = models.CharField(
        max_length=255,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )
    symbol = models.CharField(
    max_length=50
)

    def __str__(self):
        return f'{self.symbol} - {self.direction}'


class JournalEntry(models.Model):
    trade = models.OneToOneField(
        Trade,
        on_delete=models.CASCADE,
        related_name='journal'
    )

    pre_trade_analysis = models.TextField(
        blank=True
    )

    entry_reason = models.TextField(
        blank=True
    )

    market_analysis = models.TextField(
        blank=True
    )

    emotions = models.TextField(
        blank=True
    )

    exit_reason = models.TextField(
        blank=True
    )

    mistakes = models.TextField(
        blank=True
    )

    lessons = models.TextField(
        blank=True
    )

    notes = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"Journal - {self.trade}"

