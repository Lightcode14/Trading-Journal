import csv
import io

from decimal import (
    Decimal,
    InvalidOperation,
)

from django.db import transaction
from django.utils.dateparse import parse_datetime
from django.utils import timezone

from trading.models import (
    Strategy,
    Trade,
)


REQUIRED_COLUMNS = {
    "symbol",
    "direction",
    "entry_price",
    "position_size",
    "entry_time",
}


OPTIONAL_COLUMNS = {
    "status",
    "exit_price",
    "stop_loss",
    "take_profit",
    "risk_amount",
    "profit_loss",
    "fees",
    "exit_time",
    "strategy",
    "external_trade_id",
}


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


def parse_trade_datetime(
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

    parsed = parse_datetime(
        value
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


def validate_direction(
    value,
):
    value = (
        str(value)
        .strip()
        .upper()
    )

    if value not in (
        Trade.Direction.LONG,
        Trade.Direction.SHORT,
    ):
        raise ValueError(
            "direction must be LONG or SHORT."
        )

    return value


def validate_status(
    value,
):
    if value is None:
        return Trade.Status.CLOSED

    value = (
        str(value)
        .strip()
        .upper()
    )

    if not value:
        return Trade.Status.CLOSED

    if value not in (
        Trade.Status.OPEN,
        Trade.Status.CLOSED,
    ):
        raise ValueError(
            "status must be OPEN or CLOSED."
        )

    return value


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

    strategy = (
        Strategy.objects
        .filter(
            user=user,
            name__iexact=strategy_name,
        )
        .first()
    )

    if strategy is None:
        raise ValueError(
            f'Strategy "{strategy_name}" does not exist.'
        )

    return strategy


def is_duplicate_trade(
    *,
    user,
    account,
    symbol,
    entry_time,
    direction,
    external_trade_id,
):
    if external_trade_id:
        return Trade.objects.filter(
            user=user,
            account=account,
            external_trade_id=external_trade_id,
        ).exists()

    return Trade.objects.filter(
        user=user,
        account=account,
        symbol__iexact=symbol,
        direction=direction,
        entry_time=entry_time,
    ).exists()


def validate_closed_trade(
    status,
    exit_price,
    exit_time,
):
    if status != Trade.Status.CLOSED:
        return

    if exit_price is None:
        raise ValueError(
            "exit_price is required for CLOSED trades."
        )

    if exit_time is None:
        raise ValueError(
            "exit_time is required for CLOSED trades."
        )


def import_trade_csv(
    *,
    uploaded_file,
    user,
    account,
):
    try:
        decoded = uploaded_file.read().decode(
            "utf-8-sig"
        )

    except UnicodeDecodeError:
        raise ValueError(
            "The CSV file must use UTF-8 encoding."
        )


    reader = csv.DictReader(
        io.StringIO(
            decoded
        )
    )


    if not reader.fieldnames:
        raise ValueError(
            "The CSV file has no header row."
        )


    columns = {
        column.strip()
        for column in reader.fieldnames
        if column
    }


    missing_columns = (
        REQUIRED_COLUMNS -
        columns
    )


    if missing_columns:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(
                sorted(
                    missing_columns
                )
            )
        )


    prepared_trades = []

    errors = []

    skipped_duplicates = []


    for row_number, row in enumerate(
        reader,
        start=2,
    ):
        try:
            symbol = (
                str(
                    row.get(
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


            direction = (
                validate_direction(
                    row.get(
                        "direction"
                    )
                )
            )


            status = (
                validate_status(
                    row.get(
                        "status"
                    )
                )
            )


            entry_price = (
                parse_decimal(
                    row.get(
                        "entry_price"
                    ),
                    "entry_price",
                    required=True,
                )
            )


            exit_price = (
                parse_decimal(
                    row.get(
                        "exit_price"
                    ),
                    "exit_price",
                )
            )


            stop_loss = (
                parse_decimal(
                    row.get(
                        "stop_loss"
                    ),
                    "stop_loss",
                )
            )


            take_profit = (
                parse_decimal(
                    row.get(
                        "take_profit"
                    ),
                    "take_profit",
                )
            )


            position_size = (
                parse_decimal(
                    row.get(
                        "position_size"
                    ),
                    "position_size",
                    required=True,
                )
            )


            risk_amount = (
                parse_decimal(
                    row.get(
                        "risk_amount"
                    ),
                    "risk_amount",
                )
            )


            profit_loss = (
                parse_decimal(
                    row.get(
                        "profit_loss"
                    ),
                    "profit_loss",
                )
            )


            fees = (
                parse_decimal(
                    row.get(
                        "fees"
                    ),
                    "fees",
                )
            )


            if fees is None:
                fees = Decimal(
                    "0"
                )


            entry_time = (
                parse_trade_datetime(
                    row.get(
                        "entry_time"
                    ),
                    "entry_time",
                    required=True,
                )
            )


            exit_time = (
                parse_trade_datetime(
                    row.get(
                        "exit_time"
                    ),
                    "exit_time",
                )
            )


            validate_closed_trade(
                status,
                exit_price,
                exit_time,
            )


            strategy = (
                get_strategy(
                    user,
                    row.get(
                        "strategy"
                    ),
                )
            )


            external_trade_id = (
                str(
                    row.get(
                        "external_trade_id",
                        ""
                    )
                )
                .strip()
            )


            duplicate = (
                is_duplicate_trade(
                    user=user,
                    account=account,
                    symbol=symbol,
                    entry_time=entry_time,
                    direction=direction,
                    external_trade_id=external_trade_id,
                )
            )


            if duplicate:
                skipped_duplicates.append(
                    {
                        "row":
                            row_number,

                        "symbol":
                            symbol,

                        "reason":
                            "Duplicate trade",
                    }
                )

                continue


            prepared_trades.append(
                Trade(
                    user=user,

                    account=account,

                    strategy=strategy,

                    symbol=symbol,

                    direction=direction,

                    status=status,

                    entry_price=entry_price,

                    exit_price=exit_price,

                    stop_loss=stop_loss,

                    take_profit=take_profit,

                    position_size=position_size,

                    risk_amount=risk_amount,

                    profit_loss=profit_loss,

                    fees=fees,

                    entry_time=entry_time,

                    exit_time=exit_time,

                    source=Trade.Source.IMPORT,

                    external_trade_id=external_trade_id,
                )
            )


        except ValueError as exc:
            errors.append(
                {
                    "row":
                        row_number,

                    "message":
                        str(exc),
                }
            )


    if errors:
        return {
            "success":
                False,

            "created":
                0,

            "errors":
                errors,

            "duplicates":
                skipped_duplicates,
        }


    with transaction.atomic():

        created_trades = (
            Trade.objects.bulk_create(
                prepared_trades
            )
        )


    return {
        "success":
            True,

        "created":
            len(
                created_trades
            ),

        "errors":
            [],

        "duplicates":
            skipped_duplicates,
    }
def import_trade_json(
    *,
    trades_data,
    user,
    account,
):
    if not isinstance(
        trades_data,
        list
    ):
        raise ValueError(
            "trades must be a list."
        )


    prepared_trades = []

    errors = []

    skipped_duplicates = []


    for index, row in enumerate(
        trades_data,
        start=1,
    ):
        try:

            if not isinstance(
                row,
                dict
            ):
                raise ValueError(
                    "Each trade must be an object."
                )


            symbol = (
                str(
                    row.get(
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


            direction = (
                validate_direction(
                    row.get(
                        "direction"
                    )
                )
            )


            status_value = (
                row.get(
                    "status"
                )
            )


            status = (
                validate_status(
                    status_value
                )
            )


            entry_price = (
                parse_decimal(
                    row.get(
                        "entry_price"
                    ),
                    "entry_price",
                    required=True,
                )
            )


            exit_price = (
                parse_decimal(
                    row.get(
                        "exit_price"
                    ),
                    "exit_price",
                )
            )


            stop_loss = (
                parse_decimal(
                    row.get(
                        "stop_loss"
                    ),
                    "stop_loss",
                )
            )


            take_profit = (
                parse_decimal(
                    row.get(
                        "take_profit"
                    ),
                    "take_profit",
                )
            )


            position_size = (
                parse_decimal(
                    row.get(
                        "position_size"
                    ),
                    "position_size",
                    required=True,
                )
            )


            risk_amount = (
                parse_decimal(
                    row.get(
                        "risk_amount"
                    ),
                    "risk_amount",
                )
            )


            profit_loss = (
                parse_decimal(
                    row.get(
                        "profit_loss"
                    ),
                    "profit_loss",
                )
            )


            fees = (
                parse_decimal(
                    row.get(
                        "fees"
                    ),
                    "fees",
                )
            )


            if fees is None:
                fees = Decimal(
                    "0"
                )


            entry_time = (
                parse_trade_datetime(
                    row.get(
                        "entry_time"
                    ),
                    "entry_time",
                    required=True,
                )
            )


            exit_time = (
                parse_trade_datetime(
                    row.get(
                        "exit_time"
                    ),
                    "exit_time",
                )
            )


            validate_closed_trade(
                status,
                exit_price,
                exit_time,
            )


            strategy = (
                get_strategy(
                    user,
                    row.get(
                        "strategy"
                    ),
                )
            )


            external_trade_id = (
                str(
                    row.get(
                        "external_trade_id",
                        ""
                    )
                )
                .strip()
            )


            duplicate = (
                is_duplicate_trade(
                    user=user,
                    account=account,
                    symbol=symbol,
                    entry_time=entry_time,
                    direction=direction,
                    external_trade_id=external_trade_id,
                )
            )


            if duplicate:
                skipped_duplicates.append(
                    {
                        "item":
                            index,

                        "symbol":
                            symbol,

                        "reason":
                            "Duplicate trade",
                    }
                )

                continue


            prepared_trades.append(
                Trade(
                    user=user,

                    account=account,

                    strategy=strategy,

                    symbol=symbol,

                    direction=direction,

                    status=status,

                    entry_price=entry_price,

                    exit_price=exit_price,

                    stop_loss=stop_loss,

                    take_profit=take_profit,

                    position_size=position_size,

                    risk_amount=risk_amount,

                    profit_loss=profit_loss,

                    fees=fees,

                    entry_time=entry_time,

                    exit_time=exit_time,

                    source=Trade.Source.IMPORT,

                    external_trade_id=external_trade_id,
                )
            )


        except ValueError as exc:

            errors.append(
                {
                    "item":
                        index,

                    "message":
                        str(exc),
                }
            )


    if errors:
        return {
            "success":
                False,

            "created":
                0,

            "errors":
                errors,

            "duplicates":
                skipped_duplicates,
        }


    with transaction.atomic():

        created_trades = (
            Trade.objects.bulk_create(
                prepared_trades
            )
        )


    return {
        "success":
            True,

        "created":
            len(
                created_trades
            ),

        "errors":
            [],

        "duplicates":
            skipped_duplicates,
    }