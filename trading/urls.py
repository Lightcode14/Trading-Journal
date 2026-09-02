from rest_framework.routers import DefaultRouter
from .views import (EquityStatisticsView, TradingAccountViewSet,TradeViewSet,
                    JournalEntryViewSet,StrategyViewSet,
                    TradeStatisticsView,SymbolStatisticsView,
                    DirectionStatisticsView,StrategyStatisticsView,
                    TimeStatisticsView,DashboardView,GoalViewSet,
                    TradingViewWebhookView
                     
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
router.register(
    'goals',
    GoalViewSet,
    basename='goal'
)
urlpatterns = [
     path('', include(router.urls)),
    path('analytics/statistics/',TradeStatisticsView.as_view(),
          name='trade-statistics'),
    path('analytics/symbols/',SymbolStatisticsView.as_view(),
         name='symbol-statistics'),
    path('analytics/directions/',DirectionStatisticsView.as_view(),
             name='direction-statistics'),
    ## HAVENT TESTED THE FEATURES BELOW
    path('analytics/strategies/',StrategyStatisticsView.as_view(),
                 name='direction-statistics'),
    path( 'analytics/time/',TimeStatisticsView.as_view(),
         name='time-statistics'),
    path('analytics/equity/',EquityStatisticsView.as_view(),
      name='equity-statistics'),
    path(
    'dashboard/',DashboardView.as_view(),
    name='dashboard'),
    path(
    "tradingview/webhook/",
    TradingViewWebhookView.as_view(),
    name="tradingview-webhook",
),
    


               ]