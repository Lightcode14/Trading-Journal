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

    if timezone.is_naive(
        parsed
    ):
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
# FIND TRADINGVIEW TRADE
# =========================================

def find_tradingview_trade(
    *,
    account,
    external_trade_id,
):
    return (
        Trade.objects
        .filter(
            user=account.user,
            account=account,
            external_trade_id=
                external_trade_id,
            source=
                Trade.Source.TRADINGVIEW,
        )
        .first()
    )


# =========================================
# ENTRY EVENT
# =========================================

def process_entry_event(
    *,
    account,
    payload,
    external_trade_id,
):
    existing_trade = (
        find_tradingview_trade(
            account=account,
            external_trade_id=
                external_trade_id,
        )
    )


    if existing_trade:
        raise ValueError(
            "A TradingView trade with this external_trade_id already exists."
        )


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
            "symbol is required for ENTRY events."
        )


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


    entry_price = (
        parse_decimal(
            payload.get(
                "entry_price"
            ),
            "entry_price",
            required=True,
        )
    )


    position_size = (
        parse_decimal(
            payload.get(
                "position_size"
            ),
            "position_size",
            required=True,
        )
    )


    entry_time = (
        parse_datetime_value(
            payload.get(
                "entry_time"
            ),
            "entry_time",
            required=True,
        )
    )


    stop_loss = (
        parse_decimal(
            payload.get(
                "stop_loss"
            ),
            "stop_loss",
        )
    )


    take_profit = (
        parse_decimal(
            payload.get(
                "take_profit"
            ),
            "take_profit",
        )
    )


    risk_amount = (
        parse_decimal(
            payload.get(
                "risk_amount"
            ),
            "risk_amount",
        )
    )


    fees = (
        parse_decimal(
            payload.get(
                "fees"
            ),
            "fees",
        )
    )


    if fees is None:
        fees = Decimal("0")


    strategy = get_strategy(
        account.user,
        payload.get(
            "strategy"
        ),
    )


    trade = Trade.objects.create(
        user=account.user,

        account=account,

        strategy=strategy,

        symbol=symbol,

        direction=direction,

        status=Trade.Status.OPEN,

        entry_price=
            entry_price,

        position_size=
            position_size,

        stop_loss=
            stop_loss,

        take_profit=
            take_profit,

        risk_amount=
            risk_amount,

        fees=
            fees,

        entry_time=
            entry_time,

        source=
            Trade.Source.TRADINGVIEW,

        external_trade_id=
            external_trade_id,
    )


    return {
        "trade": trade,
        "created": True,
        "event": "ENTRY",
    }


# =========================================
# UPDATE EVENT
# =========================================

def process_update_event(
    *,
    account,
    payload,
    external_trade_id,
):
    trade = (
        find_tradingview_trade(
            account=account,
            external_trade_id=
                external_trade_id,
        )
    )


    if trade is None:
        raise ValueError(
            "TradingView trade not found."
        )


    if trade.status == Trade.Status.CLOSED:
        raise ValueError(
            "A closed trade cannot be updated."
        )


    update_fields = []


    if "stop_loss" in payload:
        trade.stop_loss = (
            parse_decimal(
                payload.get(
                    "stop_loss"
                ),
                "stop_loss",
            )
        )

        update_fields.append(
            "stop_loss"
        )


    if "take_profit" in payload:
        trade.take_profit = (
            parse_decimal(
                payload.get(
                    "take_profit"
                ),
                "take_profit",
            )
        )

        update_fields.append(
            "take_profit"
        )


    if "position_size" in payload:
        trade.position_size = (
            parse_decimal(
                payload.get(
                    "position_size"
                ),
                "position_size",
                required=True,
            )
        )

        update_fields.append(
            "position_size"
        )


    if "risk_amount" in payload:
        trade.risk_amount = (
            parse_decimal(
                payload.get(
                    "risk_amount"
                ),
                "risk_amount",
            )
        )

        update_fields.append(
            "risk_amount"
        )


    if "fees" in payload:
        fees = (
            parse_decimal(
                payload.get(
                    "fees"
                ),
                "fees",
            )
        )

        trade.fees = (
            fees
            if fees is not None
            else Decimal("0")
        )

        update_fields.append(
            "fees"
        )


    if "strategy" in payload:
        trade.strategy = (
            get_strategy(
                account.user,
                payload.get(
                    "strategy"
                ),
            )
        )

        update_fields.append(
            "strategy"
        )


    if not update_fields:
        raise ValueError(
            "No supported fields were provided for UPDATE."
        )


    update_fields.append(
        "updated_at"
    )


    trade.save(
        update_fields=
            update_fields
    )


    return {
        "trade": trade,
        "created": False,
        "event": "UPDATE",
    }


# =========================================
# EXIT EVENT
# =========================================

def process_exit_event(
    *,
    account,
    payload,
    external_trade_id,
):
    trade = (
        find_tradingview_trade(
            account=account,
            external_trade_id=
                external_trade_id,
        )
    )


    if trade is None:
        raise ValueError(
            "TradingView trade not found."
        )


    if trade.status == Trade.Status.CLOSED:
        raise ValueError(
            "This trade is already closed."
        )


    exit_price = (
        parse_decimal(
            payload.get(
                "exit_price"
            ),
            "exit_price",
            required=True,
        )
    )


    exit_time = (
        parse_datetime_value(
            payload.get(
                "exit_time"
            ),
            "exit_time",
            required=True,
        )
    )


    profit_loss = (
        parse_decimal(
            payload.get(
                "profit_loss"
            ),
            "profit_loss",
        )
    )


    fees = (
        parse_decimal(
            payload.get(
                "fees"
            ),
            "fees",
        )
    )


    trade.exit_price = (
        exit_price
    )

    trade.exit_time = (
        exit_time
    )

    trade.profit_loss = (
        profit_loss
    )

    trade.status = (
        Trade.Status.CLOSED
    )


    if fees is not None:
        trade.fees = fees


    trade.save(
        update_fields=[
            "exit_price",
            "exit_time",
            "profit_loss",
            "status",
            "fees",
            "updated_at",
        ]
    )


    return {
        "trade": trade,
        "created": False,
        "event": "EXIT",
    }


# =========================================
# MAIN WEBHOOK PROCESSOR
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


    event = (
        str(
            payload.get(
                "event",
                ""
            )
        )
        .strip()
        .upper()
    )


    if event not in (
        "ENTRY",
        "UPDATE",
        "EXIT",
    ):
        raise ValueError(
            "event must be ENTRY, UPDATE, or EXIT."
        )


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


    if event == "ENTRY":
        return process_entry_event(
            account=account,
            payload=payload,
            external_trade_id=
                external_trade_id,
        )


    if event == "UPDATE":
        return process_update_event(
            account=account,
            payload=payload,
            external_trade_id=
                external_trade_id,
        )


    return process_exit_event(
        account=account,
        payload=payload,
        external_trade_id=
            external_trade_id,
    )
# =========================================
# TRADINGVIEW ALERT TEMPLATES
# =========================================
def get_tradingview_templates(
    account,
):
    entry_template = {
        "event":
            "ENTRY",

        "external_trade_id":
            "TRADECRAFT_TRADE_ID",

        "symbol":
            "{{ticker}}",

        "direction":
            "LONG",

        "entry_price":
            "{{strategy.order.price}}",

        "position_size":
            "{{strategy.order.contracts}}",

        "stop_loss":
            "",

        "take_profit":
            "",

        "risk_amount":
            "",

        "entry_time":
            "{{time}}",
    }


    update_template = {
        "event":
            "UPDATE",

        "external_trade_id":
            "TRADECRAFT_TRADE_ID",

        "stop_loss":
            "",

        "take_profit":
            "",
    }


    exit_template = {
        "event":
            "EXIT",

        "external_trade_id":
            "TRADECRAFT_TRADE_ID",

        "exit_price":
            "{{strategy.order.price}}",

        "exit_time":
            "{{time}}",

        "profit_loss":
            "",

        "fees":
            "",
    }


    return {
        "entry":
            entry_template,

        "update":
            update_template,

        "exit":
            exit_template,
    }