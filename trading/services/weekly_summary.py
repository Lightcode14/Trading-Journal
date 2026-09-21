from datetime import timedelta

from django.utils import timezone

from trading.models import Notification
from trading.services.analytics import get_time_statistics
from users.models import UserPreference


def get_weekly_summary_preference(user):
    """
    Return whether Weekly Summary notifications
    are enabled for the user.

    Weekly Summary defaults to disabled if the
    user does not have a preference record.
    """

    preference = (
        UserPreference.objects
        .filter(user=user)
        .values_list(
            "weekly_summary",
            flat=True,
        )
        .first()
    )

    if preference is None:
        return False

    return bool(preference)


def get_previous_week_range():
    """
    Return the start and end of the previous
    completed calendar week.

    Week:
        Monday 00:00
        through
        next Monday 00:00

    The returned end is exclusive.
    """

    now = timezone.localtime()

    start_of_current_week = (
        now
        - timedelta(days=now.weekday())
    ).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    start_of_previous_week = (
        start_of_current_week
        - timedelta(days=7)
    )

    return (
        start_of_previous_week,
        start_of_current_week,
    )


def get_weekly_summary_data(user):
    """
    Calculate the user's trading statistics for
    the previous completed week.
    """

    start_date, end_date = (
        get_previous_week_range()
    )

    statistics = get_time_statistics(
        user=user,
        start_date=start_date,
        end_date=end_date,
    )

    return {
        "start_date": start_date,
        "end_date": end_date,
        **statistics,
    }


def build_weekly_summary_message(summary):
    """
    Build the text shown in the notification.
    """

    total_trades = summary["total_trades"]
    winning_trades = summary["winning_trades"]
    losing_trades = summary["losing_trades"]
    win_rate = summary["win_rate"]
    profit_loss = summary["total_profit_loss"]
    profit_factor = summary["profit_factor"]

    if profit_loss > 0:
        pnl_text = f"+{profit_loss:.2f}"
    else:
        pnl_text = f"{profit_loss:.2f}"

    if profit_factor is None:
        profit_factor_text = "N/A"
    else:
        profit_factor_text = (
            f"{profit_factor:.2f}"
        )

    return (
        f"You closed {total_trades} trade"
        f"{'' if total_trades == 1 else 's'} "
        f"last week with a net P&L of "
        f"{pnl_text} and a {win_rate:.2f}% "
        f"win rate. "
        f"{winning_trades} win"
        f"{'' if winning_trades == 1 else 's'}, "
        f"{losing_trades} loss"
        f"{'' if losing_trades == 1 else 'es'}. "
        f"Profit Factor: {profit_factor_text}."
    )


def create_weekly_summary_notification(user):
    """
    Create the Weekly Summary notification for
    the previous completed week.

    Only one notification can be created for
    each user/week because event_key identifies
    the week.
    """

    if not get_weekly_summary_preference(user):
        return None

    summary = get_weekly_summary_data(user)

    start_date = summary["start_date"]
    end_date = summary["end_date"]

    event_key = (
        "weekly-summary:"
        f"{start_date.date().isoformat()}:"
        f"{(end_date - timedelta(days=1)).date().isoformat()}"
    )

    existing_notification = (
        Notification.objects
        .filter(
            user=user,
            notification_type=(
                Notification.Type.WEEKLY_SUMMARY
            ),
            event_key=event_key,
        )
        .first()
    )

    if existing_notification:
        return existing_notification

    # Do not create an empty weekly summary
    # when the user had no closed trades.
    if summary["total_trades"] == 0:
        return None

    return Notification.objects.create(
        user=user,
        notification_type=(
            Notification.Type.WEEKLY_SUMMARY
        ),
        title="Weekly Trading Summary",
        message=build_weekly_summary_message(
            summary
        ),
        event_key=event_key,
    )


def check_weekly_summary(user):
    """
    Check and create the previous week's
    Weekly Summary notification when appropriate.
    """

    return create_weekly_summary_notification(
        user
    )