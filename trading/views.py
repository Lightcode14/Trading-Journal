from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.decorators import action
from .serializers import (
    TradingAccountSerializer,TradeSerializer,
    JournalEntrySerializer,StrategySerializer,GoalSerializer)
from .models import TradingAccount,Trade,JournalEntry,Strategy,Goal
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from .services.analytics import(
    get_dashboard_statistics,
    get_time_statistics,
    get_trade_statistics,
    get_symbol_statistics,
    get_direction_statistics,
    get_strategy_statistics,
    get_equity_statistics) 
from trading.services.goals import (
    calculate_goal_progress,
    calculate_goal_progress_status,
    sync_goal_status,
)
from rest_framework.views import APIView
from rest_framework.response import Response
from datetime import timedelta, datetime
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.parsers import (
    FormParser,
    MultiPartParser,
)
from rest_framework.response import Response
from rest_framework import status

from trading.models import (
    TradingAccount,
)

from trading.services.trade_import import (
    import_trade_csv,
    import_trade_json
)
from rest_framework.permissions import (
    AllowAny,
)

from trading.services.tradingview import (
    process_tradingview_webhook,
    get_tradingview_templates
)

from django_filters.rest_framework import (
    DjangoFilterBackend,
)

from rest_framework.filters import (
    OrderingFilter,
    SearchFilter,
)

class TradingAccountViewSet(
    viewsets.ModelViewSet
):
    serializer_class = (
        TradingAccountSerializer
    )

    permission_classes = [
        IsAuthenticated
    ]


    # =========================================
    # USER-OWNED ACCOUNTS ONLY
    # =========================================

    def get_queryset(
        self
    ):
        return (
            TradingAccount
            .objects
            .filter(
                user=self.request.user
            )
        )


    # =========================================
    # CREATE ACCOUNT
    # =========================================

    def perform_create(
        self,
        serializer,
    ):
        serializer.save(
            user=self.request.user
        )


    # =========================================
    # TRADINGVIEW SETTINGS
    # =========================================

    @action(
        detail=True,
        methods=["get"],
        url_path="tradingview",
    )
    def tradingview_settings(
        self,
        request,
        pk=None,
    ):
        account = (
            self.get_object()
        )


        # =====================================
        # WEBHOOK URL
        # =====================================

        webhook_url = (
            request.build_absolute_uri(
                f"/api/trading/"
                f"tradingview/"
                f"webhook/"
                f"{account.webhook_secret}/"
            )
        )


        # =====================================
        # ALERT TEMPLATES
        # =====================================

        templates = (
            get_tradingview_templates(
                account
            )
        )


        # =====================================
        # RESPONSE
        # =====================================

        return Response(
            {
                "account_id":
                    account.id,

                "account_name":
                    account.name,

                "enabled":
                    account.webhook_enabled,

                "has_secret":
                    bool(
                        account.webhook_secret
                    ),

                "webhook_secret":
                    account.webhook_secret,

                "webhook_url":
                    webhook_url,

                "templates":
                    templates,
            }
        )


    # =========================================
    # REGENERATE WEBHOOK SECRET
    # =========================================

    @action(
        detail=True,
        methods=["post"],
        url_path=(
            "tradingview/"
            "regenerate-secret"
        ),
    )
    def regenerate_webhook_secret(
        self,
        request,
        pk=None,
    ):
        account = (
            self.get_object()
        )


        account.webhook_secret = (
            secrets.token_urlsafe(
                32
            )
        )


        account.save(
            update_fields=[
                "webhook_secret",
                "updated_at",
            ]
        )


        # Build the new URL immediately
        # because the secret just changed.
        webhook_url = (
            request.build_absolute_uri(
                f"/api/trading/"
                f"tradingview/"
                f"webhook/"
                f"{account.webhook_secret}/"
            )
        )


        return Response(
            {
                "success":
                    True,

                "account_id":
                    account.id,

                "webhook_secret":
                    account.webhook_secret,

                "webhook_url":
                    webhook_url,
            }
        )


    # =========================================
    # ENABLE / DISABLE WEBHOOK
    # =========================================

    @action(
        detail=True,
        methods=["patch"],
        url_path=(
            "tradingview/status"
        ),
    )
    def update_webhook_status(
        self,
        request,
        pk=None,
    ):
        account = (
            self.get_object()
        )


        enabled = (
            request.data.get(
                "enabled"
            )
        )


        if not isinstance(
            enabled,
            bool,
        ):
            return Response(
                {
                    "detail":
                        "enabled must be true or false."
                },
                status=
                    status.HTTP_400_BAD_REQUEST,
            )


        account.webhook_enabled = (
            enabled
        )


        account.save(
            update_fields=[
                "webhook_enabled",
                "updated_at",
            ]
        )


        return Response(
            {
                "success":
                    True,

                "account_id":
                    account.id,

                "enabled":
                    account.webhook_enabled,
            }
        )
class TradeViewSet(
    viewsets.ModelViewSet
):
    serializer_class = TradeSerializer

    permission_classes = [
        IsAuthenticated
    ]

    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
    ]

    filterset_fields = [
        "account",
        "direction",
        "status",
        "strategy",
        "source",
    ]

    search_fields = [
        "symbol",
        "external_trade_id",
    ]

    ordering_fields = [
        "entry_time",
        "exit_time",
        "created_at",
        "updated_at",
        "profit_loss",
        "entry_price",
        "position_size",
    ]

    ordering = [
        "-entry_time"
    ]
    # =========================================
    # QUERYSET
    # =========================================

    def get_queryset(
        self
    ):
        return (
            Trade.objects
            .filter(
                user=self.request.user
            )
            .select_related(
                "account",
                "strategy",
            )
        )


    # =========================================
    # CREATE TRADE
    # =========================================

    def perform_create(
        self,
        serializer,
    ):
        account = (
            serializer
            .validated_data[
                "account"
            ]
        )


        if (
            account.user !=
            self.request.user
        ):
            raise PermissionDenied(
                "You do not have permission to use this trading account."
            )


        serializer.save(
            user=self.request.user
        )


    # =========================================
    # CSV IMPORT
    # =========================================

    @action(
        detail=False,
        methods=["post"],
        url_path="import",
        parser_classes=[
            MultiPartParser,
            FormParser,
        ],
    )
    def import_trades(
        self,
        request,
    ):
        uploaded_file = (
            request.FILES.get(
                "file"
            )
        )

        account_id = (
            request.data.get(
                "account"
            )
        )


        if not uploaded_file:
            return Response(
                {
                    "detail":
                        "Please upload a CSV file."
                },
                status=
                    status.HTTP_400_BAD_REQUEST,
            )


        if not account_id:
            return Response(
                {
                    "detail":
                        "Please provide a trading account."
                },
                status=
                    status.HTTP_400_BAD_REQUEST,
            )


        if (
            not uploaded_file
            .name
            .lower()
            .endswith(
                ".csv"
            )
        ):
            return Response(
                {
                    "detail":
                        "Only CSV files are supported."
                },
                status=
                    status.HTTP_400_BAD_REQUEST,
            )


        try:
            account = (
                TradingAccount.objects.get(
                    id=account_id,
                    user=request.user,
                )
            )

        except TradingAccount.DoesNotExist:
            return Response(
                {
                    "detail":
                        "Trading account not found."
                },
                status=
                    status.HTTP_404_NOT_FOUND,
            )


        try:
            result = import_trade_csv(
                uploaded_file=
                    uploaded_file,

                user=
                    request.user,

                account=
                    account,
            )

        except ValueError as exc:
            return Response(
                {
                    "detail":
                        str(exc)
                },
                status=
                    status.HTTP_400_BAD_REQUEST,
            )


        if not result["success"]:
            return Response(
                result,
                status=
                    status.HTTP_400_BAD_REQUEST,
            )


        return Response(
            result,
            status=
                status.HTTP_201_CREATED,
        )


    # =========================================
    # JSON IMPORT
    # =========================================

    @action(
        detail=False,
        methods=["post"],
        url_path="import-json",
    )
    def import_json(
        self,
        request,
    ):
        account_id = (
            request.data.get(
                "account"
            )
        )

        trades_data = (
            request.data.get(
                "trades"
            )
        )


        if not account_id:
            return Response(
                {
                    "detail":
                        "Please provide a trading account."
                },
                status=
                    status.HTTP_400_BAD_REQUEST,
            )


        if trades_data is None:
            return Response(
                {
                    "detail":
                        "Please provide trades."
                },
                status=
                    status.HTTP_400_BAD_REQUEST,
            )


        try:
            account = (
                TradingAccount.objects.get(
                    id=account_id,
                    user=request.user,
                )
            )

        except TradingAccount.DoesNotExist:
            return Response(
                {
                    "detail":
                        "Trading account not found."
                },
                status=
                    status.HTTP_404_NOT_FOUND,
            )


        try:
            result = import_trade_json(
                trades_data=
                    trades_data,

                user=
                    request.user,

                account=
                    account,
            )

        except ValueError as exc:
            return Response(
                {
                    "detail":
                        str(exc)
                },
                status=
                    status.HTTP_400_BAD_REQUEST,
            )


        if not result["success"]:
            return Response(
                result,
                status=
                    status.HTTP_400_BAD_REQUEST,
            )


        return Response(
            result,
            status=
                status.HTTP_201_CREATED,
        )

class TradingViewWebhookView(
    APIView
):
    permission_classes = [
        AllowAny
    ]


    def post(
        self,
        request,
        secret,
    ):
        # =====================================
        # FIND ENABLED TRADING ACCOUNT
        # =====================================

        try:
            account = (
                TradingAccount
                .objects
                .select_related(
                    "user"
                )
                .get(
                    webhook_secret=secret,
                    webhook_enabled=True,
                )
            )

        except TradingAccount.DoesNotExist:
            return Response(
                {
                    "detail":
                        "Invalid webhook secret or integration is disabled."
                },
                status=
                    status.HTTP_401_UNAUTHORIZED,
            )


        # =====================================
        # PROCESS TRADINGVIEW EVENT
        # =====================================

        try:
            result = (
                process_tradingview_webhook(
                    account=account,
                    payload=request.data,
                )
            )

        except ValueError as exc:
            return Response(
                {
                    "detail":
                        str(exc)
                },
                status=
                    status.HTTP_400_BAD_REQUEST,
            )


        # =====================================
        # RESULT
        # =====================================

        trade = (
            result["trade"]
        )


        return Response(
            {
                "success":
                    True,

                "event":
                    result["event"],

                "created":
                    result["created"],

                "trade_id":
                    trade.id,

                "external_trade_id":
                    trade.external_trade_id,

                "status":
                    trade.status,

                "source":
                    trade.source,
            },

            status=(
                status.HTTP_201_CREATED
                if result["created"]
                else status.HTTP_200_OK
            ),
        )
class JournalEntryViewSet(viewsets.ModelViewSet):
    serializer_class = JournalEntrySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return JournalEntry.objects.filter(
            trade__user=self.request.user
        )
    def perform_create(self, serializer):
     trade = serializer.validated_data['trade']

     if trade.user != self.request.user:
        raise PermissionDenied(
            'You do not have permission to journal this trade.'
        )

     serializer.save()

class TradeStatisticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        statistics = get_trade_statistics(request.user)

        return Response(statistics)

class SymbolStatisticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        statistics = get_symbol_statistics(request.user)

        return Response(statistics)

class DirectionStatisticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        statistics = get_direction_statistics(
            request.user
        )

        return Response(statistics)


class StrategyViewSet(viewsets.ModelViewSet):
    serializer_class = StrategySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Strategy.objects.filter(
            user=self.request.user
        )

    def perform_create(self, serializer):
        serializer.save(
            user=self.request.user
        )
class StrategyStatisticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        statistics = get_strategy_statistics(
            request.user
        )

        return Response(statistics)

class TimeStatisticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        period = request.query_params.get('period')
        start_param = request.query_params.get('start')
        end_param = request.query_params.get('end')

        now = timezone.now()

        # -------------------------
        # CUSTOM DATE RANGE
        # -------------------------
        if start_param or end_param:

            if not start_param or not end_param:
                return Response(
                    {
                        'error': (
                            'Both start and end dates '
                            'are required.'
                        )
                    },
                    status=400
                )

            try:
                start_date = datetime.strptime(
                    start_param,
                    '%Y-%m-%d'
                )

                end_date = datetime.strptime(
                    end_param,
                    '%Y-%m-%d'
                )

            except ValueError:
                return Response(
                    {
                        'error': (
                            'Invalid date format. '
                            'Use YYYY-MM-DD.'
                        )
                    },
                    status=400
                )

            # Make dates timezone-aware
            start_date = timezone.make_aware(
                start_date
            )

            end_date = timezone.make_aware(
                end_date
            ) + timedelta(days=1)

            if start_date >= end_date:
                return Response(
                    {
                        'error': (
                            'Start date must be before '
                            'end date.'
                        )
                    },
                    status=400
                )

            selected_period = 'custom'

        # -------------------------
        # PREDEFINED PERIODS
        # -------------------------
        else:

            if period == 'today':

                start_date = now.replace(
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0
                )

                end_date = start_date + timedelta(days=1)

            elif period == 'week':

                start_date = now - timedelta(
                    days=now.weekday()
                )

                start_date = start_date.replace(
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0
                )

                end_date = start_date + timedelta(days=7)

            elif period == 'month':

                start_date = now.replace(
                    day=1,
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0
                )

                if start_date.month == 12:

                    end_date = start_date.replace(
                        year=start_date.year + 1,
                        month=1
                    )

                else:

                    end_date = start_date.replace(
                        month=start_date.month + 1
                    )

            elif period == 'year':

                start_date = now.replace(
                    month=1,
                    day=1,
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0
                )

                end_date = start_date.replace(
                    year=start_date.year + 1
                )

            else:

                return Response(
                    {
                        'error': (
                            'Provide either a valid period '
                            '(today, week, month, year) '
                            'or a custom start and end date.'
                        )
                    },
                    status=400
                )

            selected_period = period

        # -------------------------
        # CALCULATE STATISTICS
        # -------------------------

        statistics = get_time_statistics(
            request.user,
            start_date,
            end_date
        )

        return Response(
            {
                'period': selected_period,
                'start_date': start_date,
                'end_date': end_date,
                'statistics': statistics
            }
        )

class EquityStatisticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        account_id = request.query_params.get('account')

        if not account_id:
            return Response(
                {
                    'error': 'account parameter is required.'
                },
                status=400
            )

        try:
            account_id = int(account_id)

        except ValueError:
            return Response(
                {
                    'error': 'account must be a valid ID.'
                },
                status=400
            )

        period = request.query_params.get('period')

        start_param = request.query_params.get('start')

        end_param = request.query_params.get('end')

        now = timezone.now()

        # ====================================================
        # CUSTOM DATE RANGE
        # ====================================================

        if start_param or end_param:

            if not start_param or not end_param:
                return Response(
                    {
                        'error': (
                            'Both start and end dates '
                            'are required.'
                        )
                    },
                    status=400
                )

            try:

                start_date = datetime.strptime(
                    start_param,
                    '%Y-%m-%d'
                )

                end_date = datetime.strptime(
                    end_param,
                    '%Y-%m-%d'
                )

            except ValueError:

                return Response(
                    {
                        'error': (
                            'Invalid date format. '
                            'Use YYYY-MM-DD.'
                        )
                    },
                    status=400
                )

            start_date = timezone.make_aware(
                start_date
            )

            end_date = timezone.make_aware(
                end_date
            ) + timedelta(days=1)

            if start_date >= end_date:

                return Response(
                    {
                        'error': (
                            'Start date must be before '
                            'end date.'
                        )
                    },
                    status=400
                )

            selected_period = 'custom'

        # ====================================================
        # PREDEFINED PERIOD
        # ====================================================

        elif period:

            if period == 'today':

                start_date = now.replace(
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0
                )

                end_date = start_date + timedelta(days=1)

            elif period == 'week':

                start_date = (
                    now -
                    timedelta(days=now.weekday())
                )

                start_date = start_date.replace(
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0
                )

                end_date = (
                    start_date +
                    timedelta(days=7)
                )

            elif period == 'month':

                start_date = now.replace(
                    day=1,
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0
                )

                if start_date.month == 12:

                    end_date = start_date.replace(
                        year=start_date.year + 1,
                        month=1
                    )

                else:

                    end_date = start_date.replace(
                        month=start_date.month + 1
                    )

            elif period == 'year':

                start_date = now.replace(
                    month=1,
                    day=1,
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0
                )

                end_date = start_date.replace(
                    year=start_date.year + 1
                )

            else:

                return Response(
                    {
                        'error': (
                            'Invalid period. Use '
                            'today, week, month, or year.'
                        )
                    },
                    status=400
                )

            selected_period = period

        # ====================================================
        # NO FILTER
        # ====================================================

        else:

            start_date = None
            end_date = None

            selected_period = 'all_time'

        # ====================================================
        # GET STATISTICS
        # ====================================================

        try:

            statistics = get_equity_statistics(
                request.user,
                account_id,
                start_date,
                end_date
            )

        except TradingAccount.DoesNotExist:

            return Response(
                {
                    'error': 'Trading account not found.'
                },
                status=404
            )

        return Response(
            {
                'account': account_id,
                'period': selected_period,
                'start_date': start_date,
                'end_date': end_date,
                'statistics': statistics
            }
        )

class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        dashboard = get_dashboard_statistics(
            request.user
        )

        return Response(dashboard)

class GoalViewSet(viewsets.ModelViewSet):
    serializer_class = GoalSerializer
    permission_classes = (
        IsAuthenticated,
    )


    def get_queryset(self):
        return (
            Goal.objects
            .filter(
                user=self.request.user
            )
            .select_related(
                "account"
            )
            .order_by(
                "-created_at"
            )
        )


    def perform_create(
        self,
        serializer,
    ):
        serializer.save(
            user=self.request.user
        )


    @action(
        detail=False,
        methods=["get"],
        url_path="summary",
    )
    def summary(
        self,
        request,
    ):
        goals = self.get_queryset()

        active_goals = 0
        completed_goals = 0
        on_track = 0
        needs_attention = 0


        for goal in goals:

            # Automatically complete
            # goals that have reached 100%.
            sync_goal_status(
                goal
            )


            if goal.status == "ACTIVE":
                active_goals += 1


            if goal.status == "COMPLETED":
                completed_goals += 1


            # Paused/completed goals should
            # not affect current performance
            # status cards.
            if goal.status != "ACTIVE":
                continue


            progress_status = (
                calculate_goal_progress_status(
                    goal
                )
            )


            if progress_status == "ON_TRACK":
                on_track += 1


            if progress_status in (
                "BEHIND",
                "CLOSE",
            ):
                needs_attention += 1


        return Response(
            {
                "active_goals":
                    active_goals,

                "completed_goals":
                    completed_goals,

                "on_track":
                    on_track,

                "needs_attention":
                    needs_attention,
            }
        )