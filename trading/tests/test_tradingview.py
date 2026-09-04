from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from trading.models import (
    Trade,
    TradingAccount,
)


User = get_user_model()


class TradingViewWebhookTests(
    APITestCase
):

    def setUp(
        self
    ):
        self.user = User.objects.create_user(
            username="tvuser",
            email="tv@example.com",
            password="testpass123",
        )

        self.account = (
            TradingAccount.objects.create(
                user=self.user,
                name="TradingView Account",
                broker="Binance",
                currency="USD",
                starting_balance="10000.00",
            )
        )

        self.secret = (
            self.account.webhook_secret
        )


    # =========================================
    # WEBHOOK URL HELPER
    # =========================================

    def webhook_url(
        self,
        secret=None,
    ):
        if secret is None:
            secret = self.secret

        return reverse(
            "tradingview-webhook",
            kwargs={
                "secret": secret
            },
        )


    # =========================================
    # ENTRY
    # =========================================

    def test_entry_creates_trade(
        self
    ):
        data = {
            "event":
                "ENTRY",

            "external_trade_id":
                "TV-TEST-001",

            "symbol":
                "BTCUSD",

            "direction":
                "LONG",

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

            "entry_time":
                "2026-09-02T10:00:00Z",
        }


        response = self.client.post(
            self.webhook_url(),
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
            trade.source,
            Trade.Source.TRADINGVIEW,
        )


        self.assertEqual(
            trade.status,
            Trade.Status.OPEN,
        )


        self.assertEqual(
            trade.external_trade_id,
            "TV-TEST-001",
        )


    # =========================================
    # UPDATE
    # =========================================

    def test_update_changes_existing_trade(
        self
    ):
        trade = (
            Trade.objects.create(
                user=self.user,
                account=self.account,
                symbol="BTCUSD",
                direction="LONG",
                status="OPEN",
                entry_price="100000.00",
                position_size="0.10",
                stop_loss="99000.00",
                take_profit="102000.00",
                entry_time="2026-09-02T10:00:00Z",
                source=Trade.Source.TRADINGVIEW,
                external_trade_id="TV-TEST-002",
            )
        )


        data = {
            "event":
                "UPDATE",

            "external_trade_id":
                "TV-TEST-002",

            "stop_loss":
                "99500.00",

            "take_profit":
                "103000.00",
        }


        response = self.client.post(
            self.webhook_url(),
            data,
            format="json",
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )


        self.assertEqual(
            Trade.objects.count(),
            1,
        )


        trade.refresh_from_db()


        self.assertEqual(
            str(trade.stop_loss),
            "99500.00000000",
        )


        self.assertEqual(
            str(trade.take_profit),
            "103000.00000000",
        )


    # =========================================
    # EXIT
    # =========================================

    def test_exit_closes_existing_trade(
        self
    ):
        trade = (
            Trade.objects.create(
                user=self.user,
                account=self.account,
                symbol="BTCUSD",
                direction="LONG",
                status="OPEN",
                entry_price="100000.00",
                position_size="0.10",
                entry_time="2026-09-02T10:00:00Z",
                source=Trade.Source.TRADINGVIEW,
                external_trade_id="TV-TEST-003",
            )
        )


        data = {
            "event":
                "EXIT",

            "external_trade_id":
                "TV-TEST-003",

            "exit_price":
                "102000.00",

            "exit_time":
                "2026-09-02T13:00:00Z",

            "profit_loss":
                "200.00",

            "fees":
                "5.00",
        }


        response = self.client.post(
            self.webhook_url(),
            data,
            format="json",
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )


        self.assertEqual(
            Trade.objects.count(),
            1,
        )


        trade.refresh_from_db()


        self.assertEqual(
            trade.status,
            Trade.Status.CLOSED,
        )


        self.assertEqual(
            str(trade.profit_loss),
            "200.00",
        )


    # =========================================
    # INVALID SECRET
    # =========================================

    def test_invalid_secret_is_rejected(
        self
    ):
        data = {
            "event":
                "ENTRY",

            "external_trade_id":
                "TV-BAD-001",

            "symbol":
                "BTCUSD",

            "direction":
                "LONG",

            "entry_price":
                "100000.00",

            "position_size":
                "0.10",

            "entry_time":
                "2026-09-02T10:00:00Z",
        }


        response = self.client.post(
            self.webhook_url(
                "invalid-secret"
            ),
            data,
            format="json",
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )


        self.assertEqual(
            Trade.objects.count(),
            0,
        )


    # =========================================
    # DISABLED WEBHOOK
    # =========================================

    def test_disabled_webhook_is_rejected(
        self
    ):
        self.account.webhook_enabled = (
            False
        )

        self.account.save(
            update_fields=[
                "webhook_enabled",
            ]
        )


        data = {
            "event":
                "ENTRY",

            "external_trade_id":
                "TV-DISABLED-001",

            "symbol":
                "BTCUSD",

            "direction":
                "LONG",

            "entry_price":
                "100000.00",

            "position_size":
                "0.10",

            "entry_time":
                "2026-09-02T10:00:00Z",
        }


        response = self.client.post(
            self.webhook_url(),
            data,
            format="json",
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )


        self.assertEqual(
            Trade.objects.count(),
            0,
        )


    # =========================================
    # DUPLICATE ENTRY
    # =========================================

    def test_duplicate_entry_is_rejected(
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
            source=Trade.Source.TRADINGVIEW,
            external_trade_id="TV-DUP-001",
        )


        data = {
            "event":
                "ENTRY",

            "external_trade_id":
                "TV-DUP-001",

            "symbol":
                "BTCUSD",

            "direction":
                "LONG",

            "entry_price":
                "100000.00",

            "position_size":
                "0.10",

            "entry_time":
                "2026-09-02T10:00:00Z",
        }


        response = self.client.post(
            self.webhook_url(),
            data,
            format="json",
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )


        self.assertEqual(
            Trade.objects.count(),
            1,
        )


    # =========================================
    # SECRET REGENERATION
    # =========================================

    def test_regenerated_secret_invalidates_old_secret(
        self
    ):
        old_secret = (
            self.account.webhook_secret
        )


        self.client.force_authenticate(
            user=self.user
        )


        regenerate_url = reverse(
            "trading-account-regenerate-webhook-secret",
            kwargs={
                "pk":
                    self.account.id
            },
        )


        response = self.client.post(
            regenerate_url
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )


        self.account.refresh_from_db()


        self.assertNotEqual(
            old_secret,
            self.account.webhook_secret,
        )


        data = {
            "event":
                "ENTRY",

            "external_trade_id":
                "TV-OLD-SECRET",

            "symbol":
                "BTCUSD",

            "direction":
                "LONG",

            "entry_price":
                "100000.00",

            "position_size":
                "0.10",

            "entry_time":
                "2026-09-02T10:00:00Z",
        }


        old_webhook_url = reverse(
            "tradingview-webhook",
            kwargs={
                "secret":
                    old_secret
            },
        )


        old_response = (
            self.client.post(
                old_webhook_url,
                data,
                format="json",
            )
        )


        self.assertEqual(
            old_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )