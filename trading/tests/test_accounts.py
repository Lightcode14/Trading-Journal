from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from trading.models import (
    TradingAccount,
)


User = get_user_model()


class TradingAccountAPITests(
    APITestCase
):

    def setUp(
        self
    ):
        # =====================================
        # USERS
        # =====================================

        self.user = User.objects.create_user(
            username="accountuser",
            email="account@example.com",
            password="testpass123",
        )

        self.other_user = User.objects.create_user(
            username="otheraccountuser",
            email="otheraccount@example.com",
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
                account_identifier="BIN-001",
                currency="USD",
                starting_balance="10000.00",
            )
        )

        self.other_account = (
            TradingAccount.objects.create(
                user=self.other_user,
                name="Other Account",
                broker="Bybit",
                account_identifier="BYBIT-001",
                currency="USD",
                starting_balance="5000.00",
            )
        )


        # =====================================
        # AUTHENTICATION
        # =====================================

        self.client.force_authenticate(
            user=self.user
        )


        # =====================================
        # URLS
        # =====================================

        self.account_list_url = reverse(
            "trading-account-list"
        )


    # =========================================
    # CREATE ACCOUNT
    # =========================================

    def test_user_can_create_trading_account(
        self
    ):
        data = {
            "name":
                "Demo Account",

            "broker":
                "Demo Broker",

            "account_identifier":
                "DEMO-001",

            "currency":
                "USD",

            "starting_balance":
                "25000.00",
        }


        response = self.client.post(
            self.account_list_url,
            data,
            format="json",
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )


        self.assertEqual(
            TradingAccount.objects.count(),
            3,
        )


        account = (
            TradingAccount.objects.get(
                name="Demo Account"
            )
        )


        self.assertEqual(
            account.user,
            self.user,
        )


    # =========================================
    # ACCOUNT LIST OWNERSHIP
    # =========================================

    def test_account_list_only_returns_authenticated_users_accounts(
        self
    ):
        response = self.client.get(
            self.account_list_url
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )


        results = response.data.get(
            "results",
            response.data,
        )


        self.assertEqual(
            len(results),
            1,
        )


        self.assertEqual(
            results[0]["id"],
            self.account.id,
        )


        self.assertEqual(
            results[0]["name"],
            "Main Account",
        )


    # =========================================
    # USER CANNOT ACCESS ANOTHER ACCOUNT
    # =========================================

    def test_user_cannot_retrieve_another_users_account(
        self
    ):
        url = reverse(
            "trading-account-detail",
            kwargs={
                "pk":
                    self.other_account.id
            },
        )


        response = self.client.get(
            url
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )


    # =========================================
    # UPDATE OWN ACCOUNT
    # =========================================

    def test_user_can_update_own_account(
        self
    ):
        url = reverse(
            "trading-account-detail",
            kwargs={
                "pk":
                    self.account.id
            },
        )


        response = self.client.patch(
            url,
            {
                "name":
                    "Updated Binance Account"
            },
            format="json",
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )


        self.account.refresh_from_db()


        self.assertEqual(
            self.account.name,
            "Updated Binance Account",
        )


    # =========================================
    # TRADINGVIEW SETTINGS
    # =========================================

    def test_user_can_get_tradingview_settings(
        self
    ):
        url = reverse(
            "trading-account-tradingview-settings",
            kwargs={
                "pk":
                    self.account.id
            },
        )


        response = self.client.get(
            url
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )


        self.assertEqual(
            response.data["account_id"],
            self.account.id,
        )


        self.assertTrue(
            response.data["has_secret"]
        )


        self.assertIn(
            "webhook_url",
            response.data,
        )


        self.assertIn(
            "templates",
            response.data,
        )


    # =========================================
    # TRADINGVIEW SETTINGS OWNERSHIP
    # =========================================

    def test_user_cannot_access_another_users_tradingview_settings(
        self
    ):
        url = reverse(
            "trading-account-tradingview-settings",
            kwargs={
                "pk":
                    self.other_account.id
            },
        )


        response = self.client.get(
            url
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )


    # =========================================
    # DISABLE TRADINGVIEW
    # =========================================

    def test_user_can_disable_tradingview_webhook(
        self
    ):
        url = reverse(
            "trading-account-update-webhook-status",
            kwargs={
                "pk":
                    self.account.id
            },
        )


        response = self.client.patch(
            url,
            {
                "enabled":
                    False
            },
            format="json",
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )


        self.account.refresh_from_db()


        self.assertFalse(
            self.account.webhook_enabled
        )


        self.assertFalse(
            response.data["enabled"]
        )


    # =========================================
    # ENABLE TRADINGVIEW
    # =========================================

    def test_user_can_enable_tradingview_webhook(
        self
    ):
        self.account.webhook_enabled = False

        self.account.save(
            update_fields=[
                "webhook_enabled",
            ]
        )


        url = reverse(
            "trading-account-update-webhook-status",
            kwargs={
                "pk":
                    self.account.id
            },
        )


        response = self.client.patch(
            url,
            {
                "enabled":
                    True
            },
            format="json",
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )


        self.account.refresh_from_db()


        self.assertTrue(
            self.account.webhook_enabled
        )


    # =========================================
    # INVALID ENABLED VALUE
    # =========================================

    def test_webhook_status_requires_boolean(
        self
    ):
        url = reverse(
            "trading-account-update-webhook-status",
            kwargs={
                "pk":
                    self.account.id
            },
        )


        response = self.client.patch(
            url,
            {
                "enabled":
                    "yes"
            },
            format="json",
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )


    # =========================================
    # REGENERATE SECRET
    # =========================================

    def test_user_can_regenerate_webhook_secret(
        self
    ):
        old_secret = (
            self.account.webhook_secret
        )


        url = reverse(
            "trading-account-regenerate-webhook-secret",
            kwargs={
                "pk":
                    self.account.id
            },
        )


        response = self.client.post(
            url
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


        self.assertEqual(
            response.data["webhook_secret"],
            self.account.webhook_secret,
        )


        self.assertIn(
            self.account.webhook_secret,
            response.data["webhook_url"],
        )


    # =========================================
    # DELETE OWN ACCOUNT
    # =========================================

    def test_user_can_delete_own_account(
        self
    ):
        url = reverse(
            "trading-account-detail",
            kwargs={
                "pk":
                    self.account.id
            },
        )


        response = self.client.delete(
            url
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )


        self.assertFalse(
            TradingAccount.objects.filter(
                id=self.account.id
            ).exists()
        )