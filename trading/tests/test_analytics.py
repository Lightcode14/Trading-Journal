from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from trading.models import (
    Strategy,
    Trade,
    TradingAccount,
)


User = get_user_model()


class AnalyticsAPITests(
    APITestCase
):

    def setUp(
        self
    ):
        self.user = User.objects.create_user(
            username="analyticsuser",
            email="analytics@example.com",
            password="testpass123",
        )

        self.other_user = User.objects.create_user(
            username="otheranalyticsuser",
            email="otheranalytics@example.com",
            password="testpass123",
        )

        self.account = TradingAccount.objects.create(
            user=self.user,
            name="Main Account",
            broker="Binance",
            currency="USD",
            starting_balance="10000.00",
        )

        self.other_account = TradingAccount.objects.create(
            user=self.other_user,
            name="Other Account",
            broker="Bybit",
            currency="USD",
            starting_balance="5000.00",
        )

        self.strategy = Strategy.objects.create(
            user=self.user,
            name="Breakout",
            description="Breakout strategy",
        )

        self.other_strategy = Strategy.objects.create(
            user=self.other_user,
            name="Scalping",
            description="Other user's strategy",
        )

        self.client.force_authenticate(
            user=self.user
        )


        # =====================================
        # USER TRADES
        # =====================================

        Trade.objects.create(
            user=self.user,
            account=self.account,
            strategy=self.strategy,
            symbol="BTCUSD",
            direction=Trade.Direction.LONG,
            status=Trade.Status.CLOSED,
            entry_price="100000.00",
            exit_price="102000.00",
            position_size="0.10",
            risk_amount="100.00",
            profit_loss="200.00",
            fees="5.00",
            entry_time="2026-09-01T10:00:00Z",
            exit_time="2026-09-01T12:00:00Z",
        )

        Trade.objects.create(
            user=self.user,
            account=self.account,
            strategy=self.strategy,
            symbol="ETHUSD",
            direction=Trade.Direction.SHORT,
            status=Trade.Status.CLOSED,
            entry_price="4200.00",
            exit_price="4300.00",
            position_size="1.00",
            risk_amount="100.00",
            profit_loss="-100.00",
            fees="3.00",
            entry_time="2026-09-02T10:00:00Z",
            exit_time="2026-09-02T12:00:00Z",
        )


        # =====================================
        # OTHER USER TRADE
        # =====================================

        Trade.objects.create(
            user=self.other_user,
            account=self.other_account,
            strategy=self.other_strategy,
            symbol="SOLUSD",
            direction=Trade.Direction.LONG,
            status=Trade.Status.CLOSED,
            entry_price="200.00",
            exit_price="250.00",
            position_size="10.00",
            risk_amount="100.00",
            profit_loss="1000.00",
            fees="2.00",
            entry_time="2026-09-02T10:00:00Z",
            exit_time="2026-09-02T12:00:00Z",
        )


    # =========================================
    # GENERAL STATISTICS
    # =========================================

    def test_statistics_endpoint_returns_user_statistics(
        self
    ):
        url = reverse(
            "trade-statistics"
        )

        response = self.client.get(
            url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertTrue(
            isinstance(
                response.data,
                dict,
            )
        )


    # =========================================
    # SYMBOL STATISTICS
    # =========================================

    def test_symbol_statistics_only_include_user_symbols(
        self
    ):
        url = reverse(
            "symbol-statistics"
        )

        response = self.client.get(
            url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        response_text = str(
            response.data
        )

        self.assertIn(
            "BTCUSD",
            response_text,
        )

        self.assertIn(
            "ETHUSD",
            response_text,
        )

        self.assertNotIn(
            "SOLUSD",
            response_text,
        )


    # =========================================
    # DIRECTION STATISTICS
    # =========================================

    def test_direction_statistics_returns_data(
        self
    ):
        url = reverse(
            "direction-statistics"
        )

        response = self.client.get(
            url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertTrue(
            response.data
        )


    # =========================================
    # STRATEGY STATISTICS
    # =========================================

    def test_strategy_statistics_only_include_user_strategy(
        self
    ):
        url = reverse(
            "strategy-statistics"
        )

        response = self.client.get(
            url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        response_text = str(
            response.data
        )

        self.assertIn(
            "Breakout",
            response_text,
        )

        self.assertNotIn(
            "Scalping",
            response_text,
        )


    # =========================================
    # TIME STATISTICS
    # =========================================

    def test_time_statistics_endpoint_works(
        self
    ):
        url = reverse(
            "time-statistics"
        )

        response = self.client.get(
            url,
            {
                "period": "month",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertTrue(
            isinstance(
                response.data,
                dict,
            )
        )


    # =========================================
    # EQUITY STATISTICS
    # =========================================

    def test_equity_statistics_endpoint_works(
        self
    ):
        url = reverse(
            "equity-statistics"
        )

        response = self.client.get(
            url,
            {
                "account":
                    self.account.id,
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertTrue(
            isinstance(
                response.data,
                dict,
            )
        )


    # =========================================
    # DASHBOARD
    # =========================================

    def test_dashboard_endpoint_works(
        self
    ):
        url = reverse(
            "dashboard"
        )

        response = self.client.get(
            url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertTrue(
            isinstance(
                response.data,
                dict,
            )
        )