from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from trading.models import Trade


def get_goal_period_bounds(goal):
    """
    Return the start and end datetime
    for the goal's selected period.
    """

    now = timezone.now()


    if goal.period == "DAILY":
        start = now.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        end = start + timedelta(days=1)

        return start, end


    if goal.period == "WEEKLY":
        start = (
            now
            - timedelta(
                days=now.weekday()
            )
        ).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        end = start + timedelta(days=7)

        return start, end


    if goal.period == "MONTHLY":
        start = now.replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        if start.month == 12:
            end = start.replace(
                year=start.year + 1,
                month=1,
            )
        else:
            end = start.replace(
                month=start.month + 1,
            )

        return start, end


    if goal.period == "QUARTERLY":
        quarter_start_month = (
            ((now.month - 1) // 3) * 3
        ) + 1

        start = now.replace(
            month=quarter_start_month,
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        if quarter_start_month == 10:
            end = start.replace(
                year=start.year + 1,
                month=1,
            )
        else:
            end = start.replace(
                month=quarter_start_month + 3,
            )

        return start, end


    if goal.period == "YEARLY":
        start = now.replace(
            month=1,
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        end = start.replace(
            year=start.year + 1
        )

        return start, end


    return None, None


def get_goal_trades(goal):
    """
    Return trades relevant to this goal,
    based on user, account, and period.
    """

    trades = Trade.objects.filter(
        user=goal.user
    )


    if goal.account:
        trades = trades.filter(
            account=goal.account
        )


    start, end = get_goal_period_bounds(
        goal
    )


    if start and end:
        trades = trades.filter(
            entry_time__gte=start,
            entry_time__lt=end,
        )


    return trades


def to_decimal(value):
    if value is None:
        return Decimal("0")

    if isinstance(value, Decimal):
        return value

    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def calculate_goal_current(goal):
    trades = get_goal_trades(
        goal
    )


    if goal.goal_type == "PROFIT":
        closed_trades = trades.filter(
            status="CLOSED"
        )

        total = Decimal("0")

        for trade in closed_trades:
            total += to_decimal(
                trade.profit_loss
            )

        return total


    if goal.goal_type == "TRADE_COUNT":
        return Decimal(
            trades.count()
        )


    if goal.goal_type == "WIN_RATE":
        closed_trades = trades.filter(
            status="CLOSED"
        )

        total_closed = (
            closed_trades.count()
        )


        if total_closed == 0:
            return Decimal("0")


        wins = (
            closed_trades.filter(
                profit_loss__gt=0
            ).count()
        )


        return (
            Decimal(wins)
            /
            Decimal(total_closed)
            *
            Decimal("100")
        )


    if (
        goal.goal_type ==
        "JOURNAL_COMPLETION"
    ):
        closed_trades = trades.filter(
            status="CLOSED"
        )


        total_closed = (
            closed_trades.count()
        )


        if total_closed == 0:
            return Decimal("0")


        journaled = (
            closed_trades.filter(
                journal__isnull=False
            ).count()
        )


        return (
            Decimal(journaled)
            /
            Decimal(total_closed)
            *
            Decimal("100")
        )


    if goal.goal_type == "MAX_LOSS":
        closed_trades = trades.filter(
            status="CLOSED",
            profit_loss__lt=0,
        )


        total_loss = Decimal("0")


        for trade in closed_trades:
            total_loss += abs(
                to_decimal(
                    trade.profit_loss
                )
            )


        return total_loss


    if (
        goal.goal_type ==
        "AVERAGE_RISK"
    ):
        trades_with_risk = (
            trades.exclude(
                risk_amount__isnull=True
            )
        )


        if (
            not trades_with_risk.exists()
        ):
            return Decimal("0")


        total_risk = Decimal("0")

        count = 0


        for trade in trades_with_risk:
            risk = to_decimal(
                trade.risk_amount
            )

            if risk > 0:
                total_risk += risk
                count += 1


        if count == 0:
            return Decimal("0")


        return (
            total_risk
            /
            Decimal(count)
        )


    return Decimal("0")


def calculate_goal_progress(
    goal,
    current=None,
):
    if current is None:
        current = calculate_goal_current(
            goal
        )


    target = to_decimal(
        goal.target
    )


    if target <= 0:
        return Decimal("0")


    if goal.goal_type in (
        "MAX_LOSS",
        "AVERAGE_RISK",
    ):
        if current <= target:
            return Decimal("100")

        progress = (
            target
            /
            current
            *
            Decimal("100")
        )

    else:
        progress = (
            current
            /
            target
            *
            Decimal("100")
        )


    if progress < 0:
        progress = Decimal("0")


    if progress > 100:
        progress = Decimal("100")


    return progress.quantize(
        Decimal("0.01")
    )


def calculate_goal_progress_status(
    goal,
    progress=None,
):
    if progress is None:
        progress = (
            calculate_goal_progress(
                goal
            )
        )


    if progress >= Decimal("100"):
        return "COMPLETED"


    if progress >= Decimal("70"):
        return "ON_TRACK"


    if progress >= Decimal("50"):
        return "CLOSE"


    return "BEHIND"


def sync_goal_status(goal):
    """
    Synchronize the stored goal lifecycle
    status with calculated progress.
    """

    if goal.status == "PAUSED":
        return goal.status


    if goal.status == "COMPLETED":
        return goal.status


    progress = calculate_goal_progress(
        goal
    )


    if progress >= Decimal("100"):
        goal.status = "COMPLETED"

        goal.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )


    return goal.status
