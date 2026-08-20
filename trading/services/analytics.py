from decimal import Decimal

from django.db.models import Sum, Avg

from trading.models import Trade,Strategy


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
        Decimal(total_trades) *
        Decimal('100')
        if total_trades
        else Decimal('0')
    )

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
        'profit_factor': (
            round(profit_factor, 2)
            if profit_factor is not None
            else None
        ),
        'average_r': round(average_r, 2),
        'expectancy': round(expectancy, 2),
    }



def calculate_win_rate(total_trades, winning_trades):
    if total_trades == 0:
        return Decimal('0')

    return (
        Decimal(winning_trades) / Decimal(total_trades)
    ) * Decimal('100')


def calculate_profit_factor(gross_profit, gross_loss):
    if gross_loss == 0:
        return None

    return gross_profit / abs(gross_loss)


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


def get_trade_statistics(user):
    trades = Trade.objects.filter(
        user=user,
        status=Trade.Status.CLOSED
    )

    return calculate_trade_metrics(trades)

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


