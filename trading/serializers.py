from rest_framework import serializers
from .models import TradingAccount,Trade,JournalEntry,Strategy

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

class TradeSerializer(serializers.ModelSerializer):

    strategy = serializers.PrimaryKeyRelatedField(
        queryset=Strategy.objects.all(),
        required=False,
        allow_null=True
    )

    # Journal is only displayed through the Trade API.
    # It cannot be created or changed through TradeSerializer.
    journal = serializers.SerializerMethodField()

    class Meta:
        model = Trade

        fields = [
            'id',
            'account',
            'user',
            'symbol',
            'direction',
            'status',
            'entry_price',
            'exit_price',
            'stop_loss',
            'take_profit',
            'position_size',
            'risk_amount',
            'profit_loss',
            'fees',
            'entry_time',
            'exit_time',
            'strategy',
            'journal',
            'setup',
            'session',
            'entry_reason',
            'exit_reason',
            'emotions',
            'mistakes',
            'lessons',
            'source',
            'external_trade_id',
            'created_at',
            'updated_at',
        ]

        read_only_fields = [
            'id',
            'user',
            'journal',
            'created_at',
            'updated_at',
        ]

    def get_journal(self, obj):

        if not hasattr(obj, 'journal'):
            return None

        return {
            'id': obj.journal.id
        }

    def validate(self, attrs):

        # -----------------------------------------
        # Strategy ownership validation
        # -----------------------------------------

        strategy = attrs.get('strategy')

        if strategy is not None:

            if strategy.user != self.context['request'].user:
                raise serializers.ValidationError({
                    'strategy': (
                        "You cannot use another user's strategy."
                    )
                })

        # -----------------------------------------
        # Trade validation
        # -----------------------------------------

        direction = attrs.get('direction')

        entry_price = attrs.get('entry_price')
        exit_price = attrs.get('exit_price')
        stop_loss = attrs.get('stop_loss')
        take_profit = attrs.get('take_profit')
        position_size = attrs.get('position_size')

        # -----------------------------------------
        # Positive value validation
        # -----------------------------------------

        if entry_price is not None and entry_price <= 0:
            raise serializers.ValidationError({
                'entry_price': (
                    'Entry price must be greater than zero.'
                )
            })

        if exit_price is not None and exit_price <= 0:
            raise serializers.ValidationError({
                'exit_price': (
                    'Exit price must be greater than zero.'
                )
            })

        if position_size is not None and position_size <= 0:
            raise serializers.ValidationError({
                'position_size': (
                    'Position size must be greater than zero.'
                )
            })

        if stop_loss is not None and stop_loss <= 0:
            raise serializers.ValidationError({
                'stop_loss': (
                    'Stop loss must be greater than zero.'
                )
            })

        if take_profit is not None and take_profit <= 0:
            raise serializers.ValidationError({
                'take_profit': (
                    'Take profit must be greater than zero.'
                )
            })

        # -----------------------------------------
        # LONG trade validation
        # -----------------------------------------

        if direction == Trade.Direction.LONG:

            if (
                stop_loss is not None
                and entry_price is not None
                and stop_loss >= entry_price
            ):
                raise serializers.ValidationError({
                    'stop_loss': (
                        'For a long trade, stop loss '
                        'should be below entry price.'
                    )
                })

            if (
                take_profit is not None
                and entry_price is not None
                and take_profit <= entry_price
            ):
                raise serializers.ValidationError({
                    'take_profit': (
                        'For a long trade, take profit '
                        'should be above entry price.'
                    )
                })

        # -----------------------------------------
        # SHORT trade validation
        # -----------------------------------------

        if direction == Trade.Direction.SHORT:

            if (
                stop_loss is not None
                and entry_price is not None
                and stop_loss <= entry_price
            ):
                raise serializers.ValidationError({
                    'stop_loss': (
                        'For a short trade, stop loss '
                        'should be above entry price.'
                    )
                })

            if (
                take_profit is not None
                and entry_price is not None
                and take_profit >= entry_price
            ):
                raise serializers.ValidationError({
                    'take_profit': (
                        'For a short trade, take profit '
                        'should be below entry price.'
                    )
                })

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