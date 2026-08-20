from django.contrib import admin
from .models import Trade, TradingAccount


@admin.register(TradingAccount)
class TradingAccountAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'user',
        'broker',
        'currency',
        'starting_balance',
        'created_at',
    )


@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = (
        'symbol',
        'direction',
        'status',
        'account',
        'profit_loss',
        'source',
        'entry_time',
    )

    list_filter = (
        'direction',
        'status',
        'source',
    )

    search_fields = (
        'symbol',
        'external_trade_id',
    )
