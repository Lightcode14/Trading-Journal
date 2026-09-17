from decimal import Decimal

from users.models import UserPreference
from trading.models import Notification, Trade, TradingAccount
from trading.services.analytics import (
    calculate_equity_curve,
    should_include_fees,
)


# ============================================================
# DRAWDOWN WARNING PREFERENCE
# ============================================================

def get_drawdown_warning_preference(user):
    """
    Return the user's drawdown warning settings.

    Returns:
        enabled: bool
        threshold: Decimal
    """

    preference = (
        UserPreference.objects
        .filter(user=user)
        .values(
            "drawdown_warnings",
            "drawdown_warning_threshold",
        )
        .first()
    )

    if preference is None:
        return True, Decimal("10")

    enabled = bool(
        preference["drawdown_warnings"]
    )

    threshold = Decimal(
        str(
            preference[
                "drawdown_warning_threshold"
            ]
        )
    )

    return enabled, threshold


# ============================================================
# ACCOUNT DRAWDOWN
# ============================================================

def get_account_drawdown_state(
    user,
    account,
):
    """
    Calculate the current and previous drawdown
    percentages for an account.

    Drawdown percentages returned here are positive
    values, e.g. 7.50 means 7.50% drawdown.
    """

    trades = (
        Trade.objects.filter(
            user=user,
            account=account,
            status=Trade.Status.CLOSED,
            exit_time__isnull=False,
            profit_loss__isnull=False,
        )
        .order_by(
            "exit_time",
            "id",
        )
    )

    include_fees = should_include_fees(
        user
    )

    equity_data = calculate_equity_curve(
        trades,
        account.starting_balance,
        include_fees=include_fees,
    )

    curve = equity_data[
        "equity_curve"
    ]

    if not curve:
        return {
            "previous_drawdown_percent":
                Decimal("0"),

            "current_drawdown_percent":
                Decimal("0"),

            "current_equity":
                Decimal(
                    str(
                        account.starting_balance
                    )
                ),

            "peak_equity":
                Decimal(
                    str(
                        account.starting_balance
                    )
                ),

            "latest_trade_id":
                None,
        }

    current_point = curve[-1]

    current_drawdown_percent = abs(
        Decimal(
            str(
                current_point[
                    "drawdown_percent"
                ]
            )
        )
    )

    if len(curve) >= 2:
        previous_point = curve[-2]

        previous_drawdown_percent = abs(
            Decimal(
                str(
                    previous_point[
                        "drawdown_percent"
                    ]
                )
            )
        )

    else:
        previous_drawdown_percent = (
            Decimal("0")
        )

    return {
        "previous_drawdown_percent":
            previous_drawdown_percent,

        "current_drawdown_percent":
            current_drawdown_percent,

        "current_equity":
            Decimal(
                str(
                    current_point[
                        "equity"
                    ]
                )
            ),

        "peak_equity":
            Decimal(
                str(
                    current_point[
                        "peak_equity"
                    ]
                )
            ),

        "latest_trade_id":
            current_point[
                "trade_id"
            ],
    }


# ============================================================
# CHECK DRAWDOWN WARNING
# ============================================================

def check_drawdown_warning(
    user,
    account,
):
    """
    Create a drawdown warning only when the account
    crosses from below the user's configured threshold
    to at-or-above that threshold.

    Example:
        Previous drawdown = 5%
        Current drawdown  = 8%
        Threshold         = 7%

        Result: create warning.

    If the account remains above 7%, additional trades
    do not create repeated warnings.

    Once the account recovers below 7%, a future crossing
    can create another warning.
    """

    if not isinstance(
        account,
        TradingAccount,
    ):
        account = (
            TradingAccount.objects.get(
                id=account,
                user=user,
            )
        )

    enabled, threshold = (
        get_drawdown_warning_preference(
            user
        )
    )

    if not enabled:
        return None

    if threshold <= 0:
        return None

    state = get_account_drawdown_state(
        user,
        account,
    )

    previous_drawdown = state[
        "previous_drawdown_percent"
    ]

    current_drawdown = state[
        "current_drawdown_percent"
    ]

    latest_trade_id = state[
        "latest_trade_id"
    ]

    if latest_trade_id is None:
        return None

    crossed_threshold = (
        previous_drawdown < threshold
        and
        current_drawdown >= threshold
    )

    if not crossed_threshold:
        return None

    event_key = (
        f"drawdown:"
        f"{account.id}:"
        f"{latest_trade_id}:"
        f"{threshold}"
    )

    existing_notification = (
        Notification.objects.filter(
            user=user,
            notification_type=
                Notification.Type.DRAWDOWN_WARNING,
            event_key=event_key,
        )
        .first()
    )

    if existing_notification:
        return existing_notification

    current_equity = state[
        "current_equity"
    ]

    peak_equity = state[
        "peak_equity"
    ]

    notification = (
        Notification.objects.create(
            user=user,

            notification_type=
                Notification.Type.DRAWDOWN_WARNING,

            title="Drawdown Warning",

            message=(
                f"{account.name} has reached "
                f"{current_drawdown:.2f}% drawdown. "
                f"Your warning threshold is "
                f"{threshold:.2f}%. "
                f"Current equity: "
                f"{account.currency} "
                f"{current_equity:.2f}. "
                f"Peak equity: "
                f"{account.currency} "
                f"{peak_equity:.2f}."
            ),

            event_key=event_key,
        )
    )

    return notification