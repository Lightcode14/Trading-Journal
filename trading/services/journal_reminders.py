from datetime import timedelta

from django.utils import timezone

from trading.models import (
    Notification,
    Trade,
)
from users.models import UserPreference


REMINDER_DELAY_HOURS = 24


def get_journal_reminder_preference(user):
    """
    Return whether journal reminders are enabled
    for the user.

    If the user does not have a preference record yet,
    reminders default to enabled.
    """

    preference = UserPreference.objects.filter(
        user=user
    ).first()

    if preference is None:
        return True

    return preference.journal_reminders


def get_trades_needing_journal_reminders(user):
    """
    Find closed trades that:

    1. Belong to the user.
    2. Were closed at least 24 hours ago.
    3. Do not have a journal entry.
    """

    reminder_cutoff = (
        timezone.now()
        - timedelta(
            hours=REMINDER_DELAY_HOURS
        )
    )

    return (
        Trade.objects.filter(
            user=user,
            status=Trade.Status.CLOSED,
            exit_time__isnull=False,
            exit_time__lte=reminder_cutoff,
            journal__isnull=True,
        )
        .select_related(
            "account"
        )
        .order_by(
            "exit_time",
            "id",
        )
    )


def create_journal_reminder(
    user,
    trade,
):
    """
    Create one journal reminder for a trade.

    event_key prevents the same trade from
    generating duplicate journal reminders.
    """

    event_key = (
        f"journal-reminder:{trade.id}"
    )

    existing_notification = (
        Notification.objects.filter(
            user=user,
            notification_type=(
                Notification.Type.JOURNAL_REMINDER
            ),
            event_key=event_key,
        )
        .first()
    )

    if existing_notification:
        return existing_notification

    account_name = (
        trade.account.name
        if trade.account
        else "your trading account"
    )

    return Notification.objects.create(
        user=user,
        notification_type=(
            Notification.Type.JOURNAL_REMINDER
        ),
        title="Complete your trade journal",
        message=(
            f"Your closed {trade.symbol} trade "
            f"on {account_name} does not have "
            f"a journal entry yet. Add your notes "
            f"while the trade is still fresh."
        ),
        event_key=event_key,
    )


def check_journal_reminders(user):
    """
    Check whether the user has any closed trades
    that need journal reminders.

    Returns a list of notifications that were
    created or already exist for eligible trades.
    """

    reminders_enabled = (
        get_journal_reminder_preference(
            user
        )
    )

    if not reminders_enabled:
        return []

    trades = (
        get_trades_needing_journal_reminders(
            user
        )
    )

    notifications = []

    for trade in trades:
        notification = (
            create_journal_reminder(
                user=user,
                trade=trade,
            )
        )

        notifications.append(
            notification
        )

    return notifications