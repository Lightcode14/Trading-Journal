from rest_framework import serializers
from .models import TradingAccount,Trade,JournalEntry,Strategy,Goal
from trading.services.goals import (
    calculate_goal_current,
    calculate_goal_progress,
    calculate_goal_progress_status,
)
class TradingAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = TradingAccount
        fields = [
            'id',
            'name',
            'broker',
            'account_identifier',
            'currency',
            'starting_balance',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'updated_at',
        ]

class TradeSerializer(
    serializers.ModelSerializer
):
    strategy = serializers.PrimaryKeyRelatedField(
        queryset=Strategy.objects.all(),
        required=False,
        allow_null=True,
    )


    class Meta:
        model = Trade

        fields = (
            "id",
            "account",
            "user",
            "strategy",
            "symbol",
            "direction",
            "status",
            "entry_price",
            "exit_price",
            "stop_loss",
            "take_profit",
            "position_size",
            "risk_amount",
            "profit_loss",
            "fees",
            "entry_time",
            "exit_time",
            "source",
            "external_trade_id",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "user",
            "created_at",
            "updated_at",
        )


    # =========================================
    # ACCOUNT OWNERSHIP
    # =========================================

    def validate_account(
        self,
        account,
    ):
        request = self.context.get(
            "request"
        )

        if (
            request
            and account.user != request.user
        ):
            raise serializers.ValidationError(
                "You cannot use another user's trading account."
            )

        return account


    # =========================================
    # STRATEGY OWNERSHIP
    # =========================================

    def validate_strategy(
        self,
        strategy,
    ):
        if strategy is None:
            return strategy

        request = self.context.get(
            "request"
        )

        if (
            request
            and strategy.user != request.user
        ):
            raise serializers.ValidationError(
                "You cannot use another user's strategy."
            )

        return strategy


    # =========================================
    # ENTRY PRICE
    # =========================================

    def validate_entry_price(
        self,
        value,
    ):
        if value <= 0:
            raise serializers.ValidationError(
                "Entry price must be greater than zero."
            )

        return value


    # =========================================
    # POSITION SIZE
    # =========================================

    def validate_position_size(
        self,
        value,
    ):
        if value <= 0:
            raise serializers.ValidationError(
                "Position size must be greater than zero."
            )

        return value


    # =========================================
    # RISK AMOUNT
    # =========================================

    def validate_risk_amount(
        self,
        value,
    ):
        if (
            value is not None
            and value < 0
        ):
            raise serializers.ValidationError(
                "Risk amount cannot be negative."
            )

        return value


    # =========================================
    # FEES
    # =========================================

    def validate_fees(
        self,
        value,
    ):
        if value < 0:
            raise serializers.ValidationError(
                "Fees cannot be negative."
            )

        return value


    # =========================================
    # COMPLETE TRADE VALIDATION
    # =========================================

    def validate(
        self,
        attrs,
    ):
        # This handles PATCH correctly.
        # If a field is not included in attrs,
        # use the existing trade value.

        instance = self.instance


        direction = attrs.get(
            "direction",
            getattr(
                instance,
                "direction",
                None,
            ),
        )

        status = attrs.get(
            "status",
            getattr(
                instance,
                "status",
                Trade.Status.CLOSED,
            ),
        )

        entry_price = attrs.get(
            "entry_price",
            getattr(
                instance,
                "entry_price",
                None,
            ),
        )

        exit_price = attrs.get(
            "exit_price",
            getattr(
                instance,
                "exit_price",
                None,
            ),
        )

        stop_loss = attrs.get(
            "stop_loss",
            getattr(
                instance,
                "stop_loss",
                None,
            ),
        )

        take_profit = attrs.get(
            "take_profit",
            getattr(
                instance,
                "take_profit",
                None,
            ),
        )

        entry_time = attrs.get(
            "entry_time",
            getattr(
                instance,
                "entry_time",
                None,
            ),
        )

        exit_time = attrs.get(
            "exit_time",
            getattr(
                instance,
                "exit_time",
                None,
            ),
        )


        # =====================================
        # CLOSED TRADE REQUIREMENTS
        # =====================================

        if status == Trade.Status.CLOSED:

            if exit_price is None:
                raise serializers.ValidationError(
                    {
                        "exit_price":
                            "Exit price is required for a closed trade."
                    }
                )

            if exit_time is None:
                raise serializers.ValidationError(
                    {
                        "exit_time":
                            "Exit time is required for a closed trade."
                    }
                )


        # =====================================
        # EXIT TIME MUST FOLLOW ENTRY TIME
        # =====================================

        if (
            entry_time is not None
            and exit_time is not None
            and exit_time < entry_time
        ):
            raise serializers.ValidationError(
                {
                    "exit_time":
                        "Exit time cannot be earlier than entry time."
                }
            )


        # =====================================
        # STOP LOSS DIRECTION VALIDATION
        # =====================================

        if (
            stop_loss is not None
            and entry_price is not None
        ):

            if (
                direction == Trade.Direction.LONG
                and stop_loss >= entry_price
            ):
                raise serializers.ValidationError(
                    {
                        "stop_loss":
                            "For a LONG trade, stop loss must be below the entry price."
                    }
                )


            if (
                direction == Trade.Direction.SHORT
                and stop_loss <= entry_price
            ):
                raise serializers.ValidationError(
                    {
                        "stop_loss":
                            "For a SHORT trade, stop loss must be above the entry price."
                    }
                )


        # =====================================
        # TAKE PROFIT DIRECTION VALIDATION
        # =====================================

        if (
            take_profit is not None
            and entry_price is not None
        ):

            if (
                direction == Trade.Direction.LONG
                and take_profit <= entry_price
            ):
                raise serializers.ValidationError(
                    {
                        "take_profit":
                            "For a LONG trade, take profit must be above the entry price."
                    }
                )


            if (
                direction == Trade.Direction.SHORT
                and take_profit >= entry_price
            ):
                raise serializers.ValidationError(
                    {
                        "take_profit":
                            "For a SHORT trade, take profit must be below the entry price."
                    }
                )


        return attrs

class JournalEntrySerializer(serializers.ModelSerializer):

    class Meta:
        model = JournalEntry

        fields = [
            'id',
            'trade',
            'pre_trade_analysis',
            'entry_reason',
            'market_analysis',
            'emotions',
            'exit_reason',
            'mistakes',
            'lessons',
            'notes',
            'created_at',
            'updated_at',
        ]

        read_only_fields = [
            'id',
            'created_at',
            'updated_at',
        ]

    def validate_trade(self, trade):

        if (
            self.instance is None
            and JournalEntry.objects.filter(
                trade=trade
            ).exists()
        ):
            raise serializers.ValidationError(
                'This trade already has a journal entry.'
            )

        return trade


class StrategySerializer(serializers.ModelSerializer):

    class Meta:
        model = Strategy

        fields = [
            'id',
            'name',
            'description',
            'created_at',
        ]

        read_only_fields = [
            'id',
            'created_at',
        ]


class GoalSerializer(
    serializers.ModelSerializer
):
    current = serializers.SerializerMethodField()

    progress = serializers.SerializerMethodField()

    progress_status = (
        serializers.SerializerMethodField()
    )


    class Meta:
        model = Goal

        fields = (
            "id",
            "title",
            "description",
            "goal_type",
            "target",
            "account",
            "period",
            "status",

            "current",
            "progress",
            "progress_status",

            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "current",
            "progress",
            "progress_status",
            "created_at",
            "updated_at",
        )


    def get_current(
        self,
        obj,
    ):
        value = (
            calculate_goal_current(
                obj
            )
        )

        return float(value)


    def get_progress(
        self,
        obj,
    ):
        value = (
            calculate_goal_progress(
                obj
            )
        )

        return float(value)


    def get_progress_status(
        self,
        obj,
    ):
        return (
            calculate_goal_progress_status(
                obj
            )
        )