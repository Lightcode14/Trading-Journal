from django.shortcuts import render
from rest_framework import viewsets
from .serializers import (
    TradingAccountSerializer,TradeSerializer,
    JournalEntrySerializer,StrategySerializer)
from .models import TradingAccount,Trade,JournalEntry,Strategy
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from .services.analytics import(
    get_time_based_statistics,
    get_trade_statistics,
    get_symbol_statistics,
    get_direction_statistics,
    get_strategy_statistics) 
from rest_framework.views import APIView
from rest_framework.response import Response


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

class TimeBasedStatisticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        statistics = get_time_based_statistics(
            request.user
        )

        return Response(statistics)