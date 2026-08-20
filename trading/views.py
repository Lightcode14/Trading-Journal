from django.shortcuts import render
from rest_framework import viewsets
from .serializers import (
    TradingAccountSerializer,TradeSerializer,
    JournalEntrySerializer,StrategySerializer)
from .models import TradingAccount,Trade,JournalEntry,Strategy
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
from rest_framework.views import APIView
from rest_framework.response import Response
from datetime import timedelta, datetime
from django.utils import timezone


class TradingAccountViewSet(viewsets.ModelViewSet):
    serializer_class= TradingAccountSerializer
    def get_queryset(self):
        return TradingAccount.objects.filter(
            user=self.request.user
        )

    def perform_create(self, serializer):
        serializer.save(
            user=self.request.user
        )

class TradeViewSet(viewsets.ModelViewSet):
    serializer_class=TradeSerializer
    permission_classes=[IsAuthenticated]
    def get_queryset(self):
        return Trade.objects.filter(
            user=self.request.user
        )

    def perform_create(self, serializer):
        account = serializer.validated_data['account']

        if account.user != self.request.user:
            raise PermissionDenied(
                'You do not have permission to use this trading account.'
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