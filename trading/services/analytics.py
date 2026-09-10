from decimal import Decimal

from django.db.models import Sum, Avg

from trading.models import (
    Trade,
    Strategy,
    TradingAccount,
)


# ============================================================
# BASIC TRADE METRICS
# ============================================================

def calculate_win_rate(
    total_trades,
    winning_trades
):
    if total_trades == 0:
        return Decimal("0")

    return (
        Decimal(winning_trades)
        / Decimal(total_trades)
    ) * Decimal("100")


def calculate_profit_factor(
    gross_profit,
    gross_loss
):
    # Profit Factor cannot be calculated until there is at least one losing trade.
    if gross_loss == 0:
        return None

    return (
        gross_profit
        / abs(gross_loss)
    )


def calculate_r_multiple(trade):
    """
    Calculate the realized R-multiple for a trade.

    Preferred formula:
        R = realized profit/loss / planned risk amount

    The stored risk_amount is the safest source because it already
    represents the monetary amount the trader intended to risk.
    This also avoids incorrect R values when Forex position size is
    stored in lots rather than raw currency units.

    For older trades that do not have risk_amount, fall back to a
    price-distance calculation. Forex lot units are expanded into
    their conventional contract sizes before calculating risk.
    """

    if trade.profit_loss is None:
        return None

    profit_loss = Decimal(
        str(trade.profit_loss)
    )

    risk_amount = getattr(
        trade,
        "risk_amount",
        None
    )

    if risk_amount is not None:
        risk_amount = abs(
            Decimal(
                str(risk_amount)
            )
        )

        if risk_amount > 0:
            return (
                profit_loss
                / risk_amount
            )

    if (
        trade.entry_price is None
        or trade.stop_loss is None
        or trade.position_size is None
    ):
        return None

    entry_price = Decimal(
        str(trade.entry_price)
    )

    stop_loss = Decimal(
        str(trade.stop_loss)
    )

    position_size = Decimal(
        str(trade.position_size)
    )

    market_type = getattr(
        trade,
        "market_type",
        None
    )

    position_size_unit = getattr(
        trade,
        "position_size_unit",
        None
    )

    effective_position_size = (
        position_size
    )

    forex_market = getattr(
        Trade.MarketType,
        "FOREX",
        "FOREX"
    )

    standard_lot = getattr(
        Trade.PositionSizeUnit,
        "STANDARD_LOT",
        "STANDARD_LOT"
    )

    mini_lot = getattr(
        Trade.PositionSizeUnit,
        "MINI_LOT",
        "MINI_LOT"
    )

    micro_lot = getattr(
        Trade.PositionSizeUnit,
        "MICRO_LOT",
        "MICRO_LOT"
    )

    if market_type == forex_market:

        if (
            position_size_unit
            == standard_lot
        ):
            effective_position_size *= (
                Decimal("100000")
            )

        elif (
            position_size_unit
            == mini_lot
        ):
            effective_position_size *= (
                Decimal("10000")
            )

        elif (
            position_size_unit
            == micro_lot
        ):
            effective_position_size *= (
                Decimal("1000")
            )

    risk_per_unit = abs(
        entry_price
        - stop_loss
    )

    total_risk = (
        risk_per_unit
        * effective_position_size
    )

    if total_risk == 0:
        return None

    return (
        profit_loss
        / total_risk
    )


def calculate_average_r(trades):
    r_multiples = [
        calculate_r_multiple(trade)
        for trade in trades
    ]

    r_multiples = [
        r
        for r in r_multiples
        if r is not None
    ]

    if not r_multiples:
        return Decimal("0")

    return (
        sum(r_multiples)
        / Decimal(
            len(r_multiples)
        )
    )


def calculate_expectancy(
    win_rate,
    loss_rate,
    average_win,
    average_loss
):
    return (
        (
            win_rate
            / Decimal("100")
        )
        * average_win
        +
        (
            loss_rate
            / Decimal("100")
        )
        * average_loss
    )


def calculate_trade_metrics(trades):

    total_trades = (
        trades.count()
    )

    winning_trades = (
        trades.filter(
            profit_loss__gt=0
        ).count()
    )

    losing_trades = (
        trades.filter(
            profit_loss__lt=0
        ).count()
    )

    total_profit_loss = (
        trades.aggregate(
            total=Sum(
                "profit_loss"
            )
        )["total"]
        or Decimal("0")
    )

    average_win = (
        trades.filter(
            profit_loss__gt=0
        ).aggregate(
            average=Avg(
                "profit_loss"
            )
        )["average"]
        or Decimal("0")
    )

    average_loss = (
        trades.filter(
            profit_loss__lt=0
        ).aggregate(
            average=Avg(
                "profit_loss"
            )
        )["average"]
        or Decimal("0")
    )

    best_trade = (
        trades.filter(
            profit_loss__isnull=False
        ).order_by(
            "-profit_loss"
        ).values_list(
            "profit_loss",
            flat=True
        ).first()
    )

    worst_trade = (
        trades.filter(
            profit_loss__isnull=False
        ).order_by(
            "profit_loss"
        ).values_list(
            "profit_loss",
            flat=True
        ).first()
    )

    gross_profit = (
        trades.filter(
            profit_loss__gt=0
        ).aggregate(
            total=Sum(
                "profit_loss"
            )
        )["total"]
        or Decimal("0")
    )

    gross_loss = (
        trades.filter(
            profit_loss__lt=0
        ).aggregate(
            total=Sum(
                "profit_loss"
            )
        )["total"]
        or Decimal("0")
    )

    win_rate = (
        calculate_win_rate(
            total_trades,
            winning_trades
        )
    )

    loss_rate = (
        (
            Decimal(losing_trades)
            / Decimal(total_trades)
        )
        * Decimal("100")
        if total_trades
        else Decimal("0")
    )

    profit_factor = (
        calculate_profit_factor(
            gross_profit,
            gross_loss
        )
    )

    average_r = (
        calculate_average_r(
            trades
        )
    )

    expectancy = (
        calculate_expectancy(
            win_rate,
            loss_rate,
            average_win,
            average_loss
        )
    )

    return {
        "total_trades":
            total_trades,

        "winning_trades":
            winning_trades,

        "losing_trades":
            losing_trades,

        "win_rate":
            round(
                win_rate,
                2
            ),

        "total_profit_loss":
            total_profit_loss,

        "average_win":
            average_win,

        "average_loss":
            average_loss,

        "best_trade":
            best_trade,

        "worst_trade":
            worst_trade,

        "profit_factor":
            (
                round(
                    profit_factor,
                    2
                )
                if profit_factor is not None
                else None
            ),

        "average_r":
            round(
                average_r,
                2
            ),

        "expectancy":
            round(
                expectancy,
                2
            ),
    }


# ============================================================
# HELPER - CLOSED TRADES
# ============================================================

def get_closed_trades(
    user,
    account_id=None
):

    trades = (
        Trade.objects.filter(
            user=user,
            status=Trade.Status.CLOSED
        )
    )

    if account_id is not None:
        trades = trades.filter(
            account_id=account_id
        )

    return trades


# ============================================================
# REALIZED ACCOUNT BALANCE
# ============================================================

def calculate_realized_account_balance(
    user,
    account,
    before_time=None
):
    """
    Return the account's realized balance.

    Realized balance =
        starting balance
        + profit/loss from closed trades.

    If before_time is provided, only trades that were closed
    before that time are included. This is used when calculating
    the monetary risk for historical trades.
    """

    trades = (
        Trade.objects.filter(
            user=user,
            account=account,
            status=Trade.Status.CLOSED,
            exit_time__isnull=False,
            profit_loss__isnull=False
        )
    )

    if before_time is not None:
        trades = trades.filter(
            exit_time__lt=before_time
        )

    realized_profit_loss = (
        trades.aggregate(
            total=Sum(
                "profit_loss"
            )
        )["total"]
        or Decimal("0")
    )

    starting_balance = Decimal(
        str(account.starting_balance)
    )

    return (
        starting_balance
        + realized_profit_loss
    )


# ============================================================
# OVERALL TRADE STATISTICS
# ============================================================

def get_trade_statistics(
    user,
    account_id=None
):

    trades = get_closed_trades(
        user,
        account_id
    )

    return (
        calculate_trade_metrics(
            trades
        )
    )


# ============================================================
# SYMBOL STATISTICS
# ============================================================

def get_symbol_statistics(
    user,
    account_id=None
):

    trades = get_closed_trades(
        user,
        account_id
    )

    symbols = (
        trades.values_list(
            "symbol",
            flat=True
        ).distinct()
    )

    results = []

    for symbol in symbols:

        symbol_trades = (
            trades.filter(
                symbol=symbol
            )
        )

        metrics = (
            calculate_trade_metrics(
                symbol_trades
            )
        )

        results.append({
            "symbol": symbol,
            **metrics,
        })

    return results


# ============================================================
# DIRECTION STATISTICS
# ============================================================

def get_direction_statistics(
    user,
    account_id=None
):

    trades = get_closed_trades(
        user,
        account_id
    )

    directions = (
        trades.values_list(
            "direction",
            flat=True
        ).distinct()
    )

    results = []

    for direction in directions:

        direction_trades = (
            trades.filter(
                direction=direction
            )
        )

        metrics = (
            calculate_trade_metrics(
                direction_trades
            )
        )

        results.append({
            "direction":
                direction,
            **metrics,
        })

    return results


# ============================================================
# STRATEGY STATISTICS
# ============================================================

def get_strategy_statistics(
    user,
    account_id=None
):

    trades = get_closed_trades(
        user,
        account_id
    ).filter(
        strategy__isnull=False
    )

    strategies = (
        trades.values_list(
            "strategy",
            flat=True
        ).distinct()
    )

    results = []

    for strategy_id in strategies:

        strategy_trades = (
            trades.filter(
                strategy_id=
                    strategy_id
            )
        )

        metrics = (
            calculate_trade_metrics(
                strategy_trades
            )
        )

        strategy = (
            Strategy.objects.get(
                id=strategy_id,
                user=user
            )
        )

        results.append({
            "strategy":
                strategy.name,
            **metrics,
        })

    return results


# ============================================================
# TIME STATISTICS
# ============================================================

def get_time_statistics(
    user,
    start_date,
    end_date,
    account_id=None
):

    trades = get_closed_trades(
        user,
        account_id
    ).filter(
        exit_time__gte=start_date,
        exit_time__lt=end_date
    )

    return (
        calculate_trade_metrics(
            trades
        )
    )


# ============================================================
# EQUITY CURVE
# ============================================================

def calculate_equity_curve(
    trades,
    starting_equity
):

    trades = trades.order_by(
        "exit_time"
    )

    equity = Decimal(
        str(starting_equity)
    )

    peak_equity = equity

    maximum_drawdown = (
        Decimal("0")
    )

    maximum_drawdown_percent = (
        Decimal("0")
    )

    curve = []

    for trade in trades:

        profit_loss = (
            trade.profit_loss
            or Decimal("0")
        )

        equity += profit_loss

        if equity > peak_equity:
            peak_equity = equity

        drawdown = (
            equity
            - peak_equity
        )

        if peak_equity != 0:
            drawdown_percent = (
                drawdown
                / peak_equity
            ) * Decimal("100")
        else:
            drawdown_percent = (
                Decimal("0")
            )

        if (
            drawdown
            < maximum_drawdown
        ):
            maximum_drawdown = (
                drawdown
            )

        if (
            drawdown_percent
            < maximum_drawdown_percent
        ):
            maximum_drawdown_percent = (
                drawdown_percent
            )

        curve.append({
            "trade_id":
                trade.id,

            "exit_time":
                trade.exit_time,

            "profit_loss":
                profit_loss,

            "equity":
                equity,

            "peak_equity":
                peak_equity,

            "drawdown":
                drawdown,

            "drawdown_percent":
                drawdown_percent,
        })

    return {
        "starting_equity":
            starting_equity,

        "ending_equity":
            equity,

        "peak_equity":
            peak_equity,

        "maximum_drawdown":
            maximum_drawdown,

        "maximum_drawdown_percent":
            maximum_drawdown_percent,

        "equity_curve":
            curve,
    }


# ============================================================
# EQUITY STATISTICS
# ============================================================

def get_equity_statistics(
    user,
    account_id,
    start_date=None,
    end_date=None
):

    account = (
        TradingAccount.objects.get(
            id=account_id,
            user=user
        )
    )

    # --------------------------------------------------------
    # Calculate equity immediately before selected period.
    #
    # For all-time statistics there are no "previous" trades,
    # so previous_profit_loss must remain zero.
    # --------------------------------------------------------

    previous_profit_loss = (
        Decimal("0")
    )

    if start_date is not None:

        previous_profit_loss = (
            Trade.objects.filter(
                user=user,
                account=account,
                status=
                    Trade.Status.CLOSED,
                exit_time__isnull=False,
                profit_loss__isnull=False,
                exit_time__lt=start_date
            ).aggregate(
                total=Sum(
                    "profit_loss"
                )
            )["total"]
            or Decimal("0")
        )

    starting_equity = (
        account.starting_balance
        + previous_profit_loss
    )

    # --------------------------------------------------------
    # Trades inside selected period
    # --------------------------------------------------------

    trades = (
        Trade.objects.filter(
            user=user,
            account=account,
            status=
                Trade.Status.CLOSED,
            exit_time__isnull=False,
            profit_loss__isnull=False
        )
    )

    if start_date is not None:

        trades = trades.filter(
            exit_time__gte=
                start_date
        )

    if end_date is not None:

        trades = trades.filter(
            exit_time__lt=
                end_date
        )

    return (
        calculate_equity_curve(
            trades,
            starting_equity
        )
    )


# ============================================================
# DASHBOARD STATISTICS
# ============================================================

def get_dashboard_statistics(
    user,
    account_id=None
):

    # --------------------------------------------------------
    # Overall statistics
    # --------------------------------------------------------

    trades = get_closed_trades(
        user,
        account_id
    )

    overview = (
        calculate_trade_metrics(
            trades
        )
    )

    # --------------------------------------------------------
    # Recent trades
    # --------------------------------------------------------

    recent_trades = (
        Trade.objects.filter(
            user=user
        )
    )

    if account_id is not None:

        recent_trades = (
            recent_trades.filter(
                account_id=
                    account_id
            )
        )

    recent_trades = (
        recent_trades.order_by(
            "-created_at"
        )[:5]
    )

    recent_trades_data = []

    for trade in recent_trades:

        recent_trades_data.append({
            "id":
                trade.id,

            "symbol":
                trade.symbol,

            "direction":
                trade.direction,

            "status":
                trade.status,

            "entry_price":
                trade.entry_price,

            "exit_price":
                trade.exit_price,

            "profit_loss":
                trade.profit_loss,

            "entry_time":
                trade.entry_time,

            "exit_time":
                trade.exit_time,
        })

    # --------------------------------------------------------
    # Trading accounts
    # --------------------------------------------------------

    accounts = (
        TradingAccount.objects.filter(
            user=user
        )
    )

    accounts_data = []

    for account in accounts:

        accounts_data.append({
            "id":
                account.id,

            "name":
                account.name,

            "broker":
                account.broker,

            "starting_balance":
                account.starting_balance,
        })

    # --------------------------------------------------------
    # Dashboard response
    # --------------------------------------------------------

    return {
        "overview":
            overview,

        "recent_trades":
            recent_trades_data,

        "accounts":
            accounts_data,
    }