from decimal import (
    Decimal,
    InvalidOperation,
)

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from trading.models import (
    Strategy,
    Trade,
)


# =========================================
# DECIMAL PARSER
# =========================================

def parse_decimal(
    value,
    field_name,
    required=False,
):
    if value is None:
        value = ""

    value = str(value).strip()

    if not value:
        if required:
            raise ValueError(
                f"{field_name} is required."
            )

        return None

    try:
        return Decimal(value)

    except InvalidOperation:
        raise ValueError(
            f"{field_name} must be a valid number."
        )


# =========================================
# DATETIME PARSER
# =========================================

def parse_datetime_value(
    value,
    field_name,
    required=False,
):
    if not value:
        if required:
            raise ValueError(
                f"{field_name} is required."
            )

        return None

    parsed = parse_datetime(
        str(value)
    )

    if parsed is None:
        raise ValueError(
            f"{field_name} must be a valid ISO datetime."
        )

    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(
            parsed,
            timezone.get_current_timezone(),
        )

    return parsed


# =========================================
# STRATEGY LOOKUP
# =========================================

def get_strategy(
    user,
    strategy_name,
):
    if not strategy_name:
        return None

    strategy_name = (
        str(strategy_name)
        .strip()
    )

    if not strategy_name:
        return None

    return (
        Strategy.objects
        .filter(
            user=user,
            name__iexact=strategy_name,
        )
        .first()
    )


# =========================================
# TRADINGVIEW WEBHOOK PROCESSOR
# =========================================

def process_tradingview_webhook(
    *,
    account,
    payload,
):
    if not isinstance(
        payload,
        dict,
    ):
        raise ValueError(
            "Invalid webhook payload."
        )


    # =====================================
    # SYMBOL
    # =====================================

    symbol = (
        str(
            payload.get(
                "symbol",
                ""
            )
        )
        .strip()
        .upper()
    )

    if not symbol:
        raise ValueError(
            "symbol is required."
        )


    # =====================================
    # DIRECTION
    # =====================================

    direction = (
        str(
            payload.get(
                "direction",
                ""
            )
        )
        .strip()
        .upper()
    )

    if direction not in (
        Trade.Direction.LONG,
        Trade.Direction.SHORT,
    ):
        raise ValueError(
            "direction must be LONG or SHORT."
        )


    # =====================================
    # STATUS
    # =====================================

    status = (
        str(
            payload.get(
                "status",
                Trade.Status.OPEN,
            )
        )
        .strip()
        .upper()
    )

    if status not in (
        Trade.Status.OPEN,
        Trade.Status.CLOSED,
    ):
        raise ValueError(
            "status must be OPEN or CLOSED."
        )


    # =====================================
    # EXTERNAL TRADE ID
    # =====================================

    external_trade_id = (
        str(
            payload.get(
                "external_trade_id",
                ""
            )
        )
        .strip()
    )

    if not external_trade_id:
        raise ValueError(
            "external_trade_id is required."
        )


    # =====================================
    # REQUIRED NUMERIC VALUES
    # =====================================

    entry_price = parse_decimal(
        payload.get(
            "entry_price"
        ),
        "entry_price",
        required=True,
    )

    position_size = parse_decimal(
        payload.get(
            "position_size"
        ),
        "position_size",
        required=True,
    )


    # =====================================
    # OPTIONAL NUMERIC VALUES
    # =====================================

    exit_price = parse_decimal(
        payload.get(
            "exit_price"
        ),
        "exit_price",
    )

    stop_loss = parse_decimal(
        payload.get(
            "stop_loss"
        ),
        "stop_loss",
    )

    take_profit = parse_decimal(
        payload.get(
            "take_profit"
        ),
        "take_profit",
    )

    risk_amount = parse_decimal(
        payload.get(
            "risk_amount"
        ),
        "risk_amount",
    )

    profit_loss = parse_decimal(
        payload.get(
            "profit_loss"
        ),
        "profit_loss",
    )

    fees = parse_decimal(
        payload.get(
            "fees"
        ),
        "fees",
    )

    if fees is None:
        fees = Decimal("0")


    # =====================================
    # TIMES
    # =====================================

    entry_time = parse_datetime_value(
        payload.get(
            "entry_time"
        ),
        "entry_time",
        required=True,
    )

    exit_time = parse_datetime_value(
        payload.get(
            "exit_time"
        ),
        "exit_time",
    )


    # =====================================
    # CLOSED TRADE VALIDATION
    # =====================================

    if status == Trade.Status.CLOSED:

        if exit_price is None:
            raise ValueError(
                "exit_price is required for CLOSED trades."
            )

        if exit_time is None:
            raise ValueError(
                "exit_time is required for CLOSED trades."
            )


    # =====================================
    # STRATEGY
    # =====================================

    strategy = get_strategy(
        account.user,
        payload.get(
            "strategy"
        ),
    )


    # =====================================
    # FIND EXISTING TRADINGVIEW TRADE
    # =====================================

    trade = (
        Trade.objects
        .filter(
            user=account.user,
            account=account,
            external_trade_id=external_trade_id,
            source=Trade.Source.TRADINGVIEW,
        )
        .first()
    )


    created = False


    # =====================================
    # CREATE IF IT DOES NOT EXIST
    # =====================================

    if trade is None:

        trade = Trade(
            user=account.user,
            account=account,
            external_trade_id=external_trade_id,
            source=Trade.Source.TRADINGVIEW,
        )

        created = True


    # =====================================
    # CREATE / UPDATE TRADE INFORMATION
    # =====================================

    trade.symbol = symbol

    trade.direction = direction

    trade.status = status

    trade.strategy = strategy

    trade.entry_price = entry_price

    trade.exit_price = exit_price

    trade.stop_loss = stop_loss

    trade.take_profit = take_profit

    trade.position_size = position_size

    trade.risk_amount = risk_amount

    trade.profit_loss = profit_loss

    trade.fees = fees

    trade.entry_time = entry_time

    trade.exit_time = exit_time

    trade.source = (
        Trade.Source.TRADINGVIEW
    )

    trade.external_trade_id = (
        external_trade_id
    )


    trade.save()


    # =====================================
    # RESULT
    # =====================================

    return {
        "trade": trade,
        "created": created,
    }