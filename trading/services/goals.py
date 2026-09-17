from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from trading.models import Trade,Notification
from users.models import UserPreference


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
        # Realized-performance goals belong to the period in
        # which the trade was closed, not when it was opened.
        realized_goal_types = (
            "PROFIT",
            "WIN_RATE",
            "JOURNAL_COMPLETION",
            "MAX_LOSS",
        )

        if goal.goal_type in realized_goal_types:
            trades = trades.filter(
                exit_time__gte=start,
                exit_time__lt=end,
            )
        else:
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


def should_include_fees(user):
    preference = (
        UserPreference.objects
        .filter(user=user)
        .values_list(
            "include_fees",
            flat=True,
        )
        .first()
    )

    if preference is None:
        return True

    return bool(preference)


def get_goal_profit_loss(
    trade,
    include_fees=True,
):
    profit_loss = to_decimal(
        trade.profit_loss
    )

    if include_fees:
        return profit_loss

    return (
        profit_loss
        + to_decimal(
            trade.fees
        )
    )


def calculate_goal_current(goal):
    trades = get_goal_trades(
        goal
    )

    include_fees = (
        should_include_fees(
            goal.user
        )
    )


    if goal.goal_type == "PROFIT":
        closed_trades = trades.filter(
            status="CLOSED"
        )

        total = Decimal("0")

        for trade in closed_trades:
            total += (
                get_goal_profit_loss(
                    trade,
                    include_fees=
                        include_fees,
                )
            )

        return total


    if goal.goal_type == "TRADE_COUNT":
        return Decimal(
            trades.count()
        )


    if goal.goal_type == "WIN_RATE":
        closed_trades = list(
            trades.filter(
                status="CLOSED"
            )
        )

        total_closed = len(
            closed_trades
        )


        if total_closed == 0:
            return Decimal("0")


        wins = 0

        for trade in closed_trades:
            if (
                get_goal_profit_loss(
                    trade,
                    include_fees=
                        include_fees,
                )
                > 0
            ):
                wins += 1


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
            status="CLOSED"
        )


        total_loss = Decimal("0")


        for trade in closed_trades:
            profit_loss = (
                get_goal_profit_loss(
                    trade,
                    include_fees=
                        include_fees,
                )
            )

            if profit_loss < 0:
                total_loss += abs(
                    profit_loss
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
    status with calculated progress and
    create a goal notification when the
    target is reached.
    """

    if goal.status == "PAUSED":
        return goal.status

    was_completed = (
        goal.status == "COMPLETED"
    )

    progress = calculate_goal_progress(
        goal
    )

    if progress >= Decimal("100"):

        if not was_completed:
            goal.status = "COMPLETED"

            goal.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

        if (
            not was_completed
            and should_send_goal_alerts(
                goal.user
            )
        ):
            start, end = (
                get_goal_period_bounds(
                    goal
                )
            )

            if start is not None:
                event_key = (
                    start.date().isoformat()
                )
            else:
                event_key = (
                    f"goal-{goal.id}"
                )

            Notification.objects.get_or_create(
                user=goal.user,
                notification_type=(
                    Notification.Type.GOAL_REACHED
                ),
                goal=goal,
                event_key=event_key,
                defaults={
                    "title":
                        "Trading Goal Reached",

                    "message":
                        (
                            f'You reached your '
                            f'"{goal.title}" goal.'
                        ),
                },
            )

    elif was_completed:
        # Repair a completed goal if recalculation shows that
        # it is no longer at 100%.
        goal.status = "ACTIVE"

        goal.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

    return goal.status
def should_send_goal_alerts(user):
    """
    Return whether the user has enabled
    Trading Goal Alerts.
    """

    preference = (
        UserPreference.objects
        .filter(user=user)
        .values_list(
            "goal_alerts",
            flat=True,
        )
        .first()
    )

    if preference is None:
        return True

    return bool(preference)


def sync_user_goals(
    user,
    account=None,
):
    """
    Recalculate the user's active goals and
    synchronize their statuses.

    If an account is provided, check:
    - goals belonging to that account
    - goals that apply to all accounts
    """

    from trading.models import Goal


    goals = Goal.objects.filter(
        user=user,
        status="ACTIVE",
    )


    if account is not None:

        from django.db.models import Q

        goals = goals.filter(
            Q(account=account)
            |
            Q(account__isnull=True)
        )


    for goal in goals:
        sync_goal_status(goal)