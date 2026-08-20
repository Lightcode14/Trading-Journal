from rest_framework.routers import DefaultRouter
from .views import (TradingAccountViewSet,TradeViewSet,
                    JournalEntryViewSet,StrategyViewSet,
                    TradeStatisticsView,SymbolStatisticsView,
                    DirectionStatisticsView,StrategyStatisticsView,
                    TimeBasedStatisticsView,
)
from django.urls import path,include
router = DefaultRouter()

router.register(
    'accounts',
    TradingAccountViewSet,
    basename='trading-account'
)
router.register(
    'trades',
    TradeViewSet,
    basename='trade'
)
router.register(
    'journal',
    JournalEntryViewSet,
    basename='journal'
)
router.register(
    'strategies',
    StrategyViewSet,
    basename='strategy'
)
urlpatterns = [
     path('', include(router.urls)),
    path('analytics/statistics/',TradeStatisticsView.as_view(),
          name='trade-statistics'),
    path('analytics/symbols/',SymbolStatisticsView.as_view(),
         name='symbol-statistics'),
    path('analytics/directions/',DirectionStatisticsView.as_view(),
             name='direction-statistics'),
    path('analytics/strategies/',StrategyStatisticsView.as_view(),
                 name='direction-statistics'),
    path('analytics/time-based/',TimeBasedStatisticsView.as_view(),
                 name='direction-statistics')
    


               ]