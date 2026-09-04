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


class TradeAPITests(
    APITestCase
):

    def setUp(
        self
    ):
        # =====================================
        # USERS
        # =====================================

        self.user = User.objects.create_user(
            username="testuser",
            email="user@example.com",
            password="testpass123",
        )

        self.other_user = User.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password="testpass123",
        )


        # =====================================
        # ACCOUNTS
        # =====================================

        self.account = (
            TradingAccount.objects.create(
                user=self.user,
                name="Main Account",
                broker="Binance",
                currency="USD",
                starting_balance="10000.00",
            )
        )

        self.other_account = (
            TradingAccount.objects.create(
                user=self.other_user,
                name="Other Account",
                broker="Binance",
                currency="USD",
                starting_balance="5000.00",
            )
        )


        # =====================================
        # STRATEGIES
        # =====================================

        self.strategy = (
            Strategy.objects.create(
                user=self.user,
                name="Breakout",
                description="Breakout strategy",
            )
        )

        self.other_strategy = (
            Strategy.objects.create(
                user=self.other_user,
                name="Scalping",
                description="Other user's strategy",
            )
        )


        # =====================================
        # AUTHENTICATION
        # =====================================

        self.client.force_authenticate(
            user=self.user
        )


        # =====================================
        # ENDPOINT
        # =====================================

        self.trade_list_url = reverse(
            "trade-list"
        )


    # =========================================
    # VALID TRADE CREATION
    # =========================================

    def test_user_can_create_trade(
        self
    ):
        data = {
            "account":
                self.account.id,

            "strategy":
                self.strategy.id,

            "symbol":
                "BTCUSD",

            "direction":
                "LONG",

            "status":
                "OPEN",

            "entry_price":
                "100000.00",

            "position_size":
                "0.10",

            "stop_loss":
                "99000.00",

            "take_profit":
                "102000.00",

            "risk_amount":
                "100.00",

            "fees":
                "2.00",

            "entry_time":
                "2026-09-02T10:00:00Z",
        }


        response = self.client.post(
            self.trade_list_url,
            data,
            format="json",
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )


        self.assertEqual(
            Trade.objects.count(),
            1,
        )


        trade = (
            Trade.objects.first()
        )


        self.assertEqual(
            trade.user,
            self.user,
        )


        self.assertEqual(
            trade.account,
            self.account,
        )


    # =========================================
    # ACCOUNT OWNERSHIP
    # =========================================

    def test_user_cannot_use_another_users_account(
        self
    ):
        data = {
            "account":
                self.other_account.id,

            "symbol":
                "BTCUSD",

            "direction":
                "LONG",

            "status":
                "OPEN",

            "entry_price":
                "100000.00",

            "position_size":
                "0.10",

            "entry_time":
                "2026-09-02T10:00:00Z",
        }


        response = self.client.post(
            self.trade_list_url,
            data,
            format="json",
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )


        self.assertEqual(
            Trade.objects.count(),
            0,
        )


    # =========================================
    # STRATEGY OWNERSHIP
    # =========================================

    def test_user_cannot_use_another_users_strategy(
        self
    ):
        data = {
            "account":
                self.account.id,

            "strategy":
                self.other_strategy.id,

            "symbol":
                "BTCUSD",

            "direction":
                "LONG",

            "status":
                "OPEN",

            "entry_price":
                "100000.00",

            "position_size":
                "0.10",

            "entry_time":
                "2026-09-02T10:00:00Z",
        }


        response = self.client.post(
            self.trade_list_url,
            data,
            format="json",
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )


        self.assertEqual(
            Trade.objects.count(),
            0,
        )


    # =========================================
    # ENTRY PRICE VALIDATION
    # =========================================

    def test_negative_entry_price_is_rejected(
        self
    ):
        data = {
            "account":
                self.account.id,

            "symbol":
                "BTCUSD",

            "direction":
                "LONG",

            "status":
                "OPEN",

            "entry_price":
                "-100",

            "position_size":
                "0.10",

            "entry_time":
                "2026-09-02T10:00:00Z",
        }


        response = self.client.post(
            self.trade_list_url,
            data,
            format="json",
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )


    # =========================================
    # POSITION SIZE VALIDATION
    # =========================================

    def test_zero_position_size_is_rejected(
        self
    ):
        data = {
            "account":
                self.account.id,

            "symbol":
                "BTCUSD",

            "direction":
                "LONG",

            "status":
                "OPEN",

            "entry_price":
                "100000.00",

            "position_size":
                "0",

            "entry_time":
                "2026-09-02T10:00:00Z",
        }


        response = self.client.post(
            self.trade_list_url,
            data,
            format="json",
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )


    # =========================================
    # CLOSED TRADE VALIDATION
    # =========================================

    def test_closed_trade_requires_exit_data(
        self
    ):
        data = {
            "account":
                self.account.id,

            "symbol":
                "BTCUSD",

            "direction":
                "LONG",

            "status":
                "CLOSED",

            "entry_price":
                "100000.00",

            "position_size":
                "0.10",

            "entry_time":
                "2026-09-02T10:00:00Z",
        }


        response = self.client.post(
            self.trade_list_url,
            data,
            format="json",
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )


        self.assertIn(
            "exit_price",
            response.data,
        )


    # =========================================
    # USER DATA ISOLATION
    # =========================================

    def test_trade_list_only_returns_authenticated_users_trades(
        self
    ):
        Trade.objects.create(
            user=self.user,
            account=self.account,
            symbol="BTCUSD",
            direction="LONG",
            status="OPEN",
            entry_price="100000.00",
            position_size="0.10",
            entry_time="2026-09-02T10:00:00Z",
        )


        Trade.objects.create(
            user=self.other_user,
            account=self.other_account,
            symbol="ETHUSD",
            direction="SHORT",
            status="OPEN",
            entry_price="4000.00",
            position_size="1.00",
            entry_time="2026-09-02T11:00:00Z",
        )


        response = self.client.get(
            self.trade_list_url
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )


        self.assertEqual(
            response.data["count"],
            1,
        )


        self.assertEqual(
            response.data["results"][0]["symbol"],
            "BTCUSD",
        )