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

def calculate_win_rate(total_trades, winning_trades):
    if total_trades == 0:
        return Decimal('0')

    return (
        Decimal(winning_trades) /
        Decimal(total_trades)
    ) * Decimal('100')


def calculate_profit_factor(gross_profit, gross_loss):
    if gross_loss == 0:
        return Decimal('0')

    return gross_profit / abs(gross_loss)


def calculate_r_multiple(trade):
    if (
        trade.entry_price is None
        or trade.stop_loss is None
        or trade.position_size is None
        or trade.profit_loss is None
    ):
        return None

    entry_price = Decimal(str(trade.entry_price))
    stop_loss = Decimal(str(trade.stop_loss))
    position_size = Decimal(str(trade.position_size))
    profit_loss = Decimal(str(trade.profit_loss))

    risk_per_unit = abs(entry_price - stop_loss)

    total_risk = risk_per_unit * position_size

    if total_risk == 0:
        return None

    return profit_loss / total_risk


def calculate_average_r(trades):
    r_multiples = [
        calculate_r_multiple(trade)
        for trade in trades
    ]

    r_multiples = [
        r for r in r_multiples
        if r is not None
    ]

    if not r_multiples:
        return Decimal('0')

    return sum(r_multiples) / Decimal(len(r_multiples))


def calculate_expectancy(
    win_rate,
    loss_rate,
    average_win,
    average_loss
):
    return (
        (win_rate / Decimal('100')) * average_win
        + (loss_rate / Decimal('100')) * average_loss
    )


def calculate_trade_metrics(trades):

    total_trades = trades.count()

    winning_trades = trades.filter(
        profit_loss__gt=0
    ).count()

    losing_trades = trades.filter(
        profit_loss__lt=0
    ).count()

    total_profit_loss = trades.aggregate(
        total=Sum('profit_loss')
    )['total'] or Decimal('0')

    average_win = trades.filter(
        profit_loss__gt=0
    ).aggregate(
        average=Avg('profit_loss')
    )['average'] or Decimal('0')

    average_loss = trades.filter(
        profit_loss__lt=0
    ).aggregate(
        average=Avg('profit_loss')
    )['average'] or Decimal('0')

    gross_profit = trades.filter(
        profit_loss__gt=0
    ).aggregate(
        total=Sum('profit_loss')
    )['total'] or Decimal('0')

    gross_loss = trades.filter(
        profit_loss__lt=0
    ).aggregate(
        total=Sum('profit_loss')
    )['total'] or Decimal('0')

    win_rate = calculate_win_rate(
        total_trades,
        winning_trades
    )

    loss_rate = (
        Decimal(losing_trades) /
        Decimal(total_trades)
    ) * Decimal('100') if total_trades else Decimal('0')

    profit_factor = calculate_profit_factor(
        gross_profit,
        gross_loss
    )

    average_r = calculate_average_r(trades)

    expectancy = calculate_expectancy(
        win_rate,
        loss_rate,
        average_win,
        average_loss
    )

    return {
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'win_rate': round(win_rate, 2),
        'total_profit_loss': total_profit_loss,
        'average_win': average_win,
        'average_loss': average_loss,
        'profit_factor': round(profit_factor, 2),
        'average_r': round(average_r, 2),
        'expectancy': round(expectancy, 2),
    }


# ============================================================
# OVERALL TRADE STATISTICS
# ============================================================

def get_trade_statistics(user):

    trades = Trade.objects.filter(
        user=user,
        status=Trade.Status.CLOSED
    )

    return calculate_trade_metrics(trades)


# ============================================================
# SYMBOL STATISTICS
# ============================================================

def get_symbol_statistics(user):

    trades = Trade.objects.filter(
        user=user,
        status=Trade.Status.CLOSED
    )

    symbols = trades.values_list(
        'symbol',
        flat=True
    ).distinct()

    results = []

    for symbol in symbols:

        symbol_trades = trades.filter(
            symbol=symbol
        )

        metrics = calculate_trade_metrics(
            symbol_trades
        )

        results.append({
            'symbol': symbol,
            **metrics
        })

    return results


# ============================================================
# DIRECTION STATISTICS
# ============================================================

def get_direction_statistics(user):

    trades = Trade.objects.filter(
        user=user,
        status=Trade.Status.CLOSED
    )

    directions = trades.values_list(
        'direction',
        flat=True
    ).distinct()

    results = []

    for direction in directions:

        direction_trades = trades.filter(
            direction=direction
        )

        metrics = calculate_trade_metrics(
            direction_trades
        )

        results.append({
            'direction': direction,
            **metrics
        })

    return results


# ============================================================
# STRATEGY STATISTICS
# ============================================================

def get_strategy_statistics(user):

    trades = Trade.objects.filter(
        user=user,
        status=Trade.Status.CLOSED,
        strategy__isnull=False
    )

    strategies = trades.values_list(
        'strategy',
        flat=True
    ).distinct()

    results = []

    for strategy_id in strategies:

        strategy_trades = trades.filter(
            strategy_id=strategy_id
        )

        metrics = calculate_trade_metrics(
            strategy_trades
        )

        strategy = Strategy.objects.get(
            id=strategy_id
        )

        results.append({
            'strategy': strategy.name,
            **metrics
        })

    return results


# ============================================================
# TIME STATISTICS
# ============================================================

def get_time_statistics(
    user,
    start_date,
    end_date
):

    trades = Trade.objects.filter(
        user=user,
        status=Trade.Status.CLOSED,
        exit_time__gte=start_date,
        exit_time__lt=end_date
    )

    return calculate_trade_metrics(trades)


# ============================================================
# EQUITY CURVE
# ============================================================

def calculate_equity_curve(
    trades,
    starting_equity
):
    trades = trades.order_by('exit_time')

    equity = Decimal(str(starting_equity))
    peak_equity = equity

    maximum_drawdown = Decimal('0')
    maximum_drawdown_percent = Decimal('0')

    curve = []

    for trade in trades:

        profit_loss = (
            trade.profit_loss
            or Decimal('0')
        )

        equity += profit_loss

        if equity > peak_equity:
            peak_equity = equity

        drawdown = equity - peak_equity

        if peak_equity != 0:
            drawdown_percent = (
                drawdown / peak_equity
            ) * Decimal('100')
        else:
            drawdown_percent = Decimal('0')

        if drawdown < maximum_drawdown:
            maximum_drawdown = drawdown

        if drawdown_percent < maximum_drawdown_percent:
            maximum_drawdown_percent = drawdown_percent

        curve.append({
            'trade_id': trade.id,
            'exit_time': trade.exit_time,
            'profit_loss': profit_loss,
            'equity': equity,
            'peak_equity': peak_equity,
            'drawdown': drawdown,
            'drawdown_percent': drawdown_percent,
        })

    return {
        'starting_equity': starting_equity,
        'ending_equity': equity,
        'peak_equity': peak_equity,
        'maximum_drawdown': maximum_drawdown,
        'maximum_drawdown_percent': maximum_drawdown_percent,
        'equity_curve': curve,
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

    account = TradingAccount.objects.get(
        id=account_id,
        user=user
    )

    # --------------------------------------------------------
    # All closed trades before the selected period
    # --------------------------------------------------------

    previous_trades = Trade.objects.filter(
        user=user,
        account=account,
        status=Trade.Status.CLOSED,
        exit_time__isnull=False,
        profit_loss__isnull=False
    )

    if start_date is not None:

        previous_trades = previous_trades.filter(
            exit_time__lt=start_date
        )

    previous_profit_loss = (
        previous_trades.aggregate(
            total=Sum('profit_loss')
        )['total']
        or Decimal('0')
    )

    # --------------------------------------------------------
    # Equity at the beginning of selected period
    # --------------------------------------------------------

    starting_equity = (
        account.starting_balance
        + previous_profit_loss
    )

    # --------------------------------------------------------
    # Trades inside selected period
    # --------------------------------------------------------

    trades = Trade.objects.filter(
        user=user,
        account=account,
        status=Trade.Status.CLOSED,
        exit_time__isnull=False,
        profit_loss__isnull=False
    )

    if start_date is not None:

        trades = trades.filter(
            exit_time__gte=start_date
        )

    if end_date is not None:

        trades = trades.filter(
            exit_time__lt=end_date
        )

    return calculate_equity_curve(
        trades,
        starting_equity
    )

# ============================================================
# DASHBOARD STATISTICS
# ============================================================

def get_dashboard_statistics(user):

    # --------------------------------------------------------
    # Overall statistics
    # --------------------------------------------------------

    trades = Trade.objects.filter(
        user=user,
        status=Trade.Status.CLOSED
    )

    overview = calculate_trade_metrics(
        trades
    )

    # --------------------------------------------------------
    # Recent trades
    # --------------------------------------------------------

    recent_trades = Trade.objects.filter(
        user=user
    ).order_by(
        '-created_at'
    )[:5]

    recent_trades_data = []

    for trade in recent_trades:

        recent_trades_data.append({
            'id': trade.id,
            'symbol': trade.symbol,
            'direction': trade.direction,
            'status': trade.status,
            'entry_price': trade.entry_price,
            'exit_price': trade.exit_price,
            'profit_loss': trade.profit_loss,
            'entry_time': trade.entry_time,
            'exit_time': trade.exit_time,
        })

    # --------------------------------------------------------
    # Trading accounts
    # --------------------------------------------------------

    accounts = TradingAccount.objects.filter(
        user=user
    )

    accounts_data = []

    for account in accounts:

        accounts_data.append({
            'id': account.id,
            'name': account.name,
            'broker': account.broker,
            'starting_balance': account.starting_balance,
        })

    # --------------------------------------------------------
    # Dashboard response
    # --------------------------------------------------------

    return {
        'overview': overview,

        'recent_trades': recent_trades_data,

        'accounts': accounts_data,
    }