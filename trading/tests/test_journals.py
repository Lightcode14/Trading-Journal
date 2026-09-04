from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from trading.models import (
    JournalEntry,
    Trade,
    TradingAccount,
)


User = get_user_model()


class JournalAPITests(
    APITestCase
):

    def setUp(
        self
    ):
        self.user = User.objects.create_user(
            username="journaluser",
            email="journal@example.com",
            password="testpass123",
        )

        self.other_user = User.objects.create_user(
            username="otherjournaluser",
            email="otherjournal@example.com",
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

        self.trade = Trade.objects.create(
            user=self.user,
            account=self.account,
            symbol="BTCUSD",
            direction=Trade.Direction.LONG,
            status=Trade.Status.CLOSED,
            entry_price="100000.00",
            exit_price="102000.00",
            position_size="0.10",
            profit_loss="200.00",
            entry_time="2026-09-02T10:00:00Z",
            exit_time="2026-09-02T12:00:00Z",
        )

        self.other_trade = Trade.objects.create(
            user=self.other_user,
            account=self.other_account,
            symbol="ETHUSD",
            direction=Trade.Direction.SHORT,
            status=Trade.Status.CLOSED,
            entry_price="4200.00",
            exit_price="4100.00",
            position_size="1.00",
            profit_loss="100.00",
            entry_time="2026-09-02T11:00:00Z",
            exit_time="2026-09-02T13:00:00Z",
        )

        self.client.force_authenticate(
            user=self.user
        )

        self.journal_list_url = reverse(
            "journal-list"
        )


    # =========================================
    # CREATE JOURNAL
    # =========================================

    def test_user_can_create_journal_for_own_trade(
        self
    ):
        data = {
            "trade": self.trade.id,
            "pre_trade_analysis":
                "Price was testing resistance.",
            "entry_reason":
                "Breakout confirmation.",
            "market_analysis":
                "Bullish structure.",
            "emotions":
                "Calm",
            "exit_reason":
                "Take profit reached.",
            "mistakes":
                "",
            "lessons":
                "Wait for confirmation.",
            "notes":
                "Good execution.",
        }

        response = self.client.post(
            self.journal_list_url,
            data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            JournalEntry.objects.count(),
            1,
        )

        journal = JournalEntry.objects.first()

        self.assertEqual(
            journal.trade,
            self.trade,
        )


    # =========================================
    # CANNOT JOURNAL ANOTHER USER'S TRADE
    # =========================================

    def test_user_cannot_create_journal_for_another_users_trade(
        self
    ):
        data = {
            "trade": self.other_trade.id,
            "notes":
                "Should not work.",
        }

        response = self.client.post(
            self.journal_list_url,
            data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.assertEqual(
            JournalEntry.objects.count(),
            0,
        )


    # =========================================
    # ONE JOURNAL PER TRADE
    # =========================================

    def test_duplicate_journal_for_same_trade_is_rejected(
        self
    ):
        JournalEntry.objects.create(
            trade=self.trade,
            notes="Original journal.",
        )

        data = {
            "trade": self.trade.id,
            "notes":
                "Duplicate journal.",
        }

        response = self.client.post(
            self.journal_list_url,
            data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            JournalEntry.objects.count(),
            1,
        )


    # =========================================
    # LIST USER JOURNALS ONLY
    # =========================================

    def test_journal_list_only_returns_authenticated_users_journals(
        self
    ):
        JournalEntry.objects.create(
            trade=self.trade,
            notes="My journal.",
        )

        JournalEntry.objects.create(
            trade=self.other_trade,
            notes="Other user's journal.",
        )

        response = self.client.get(
            self.journal_list_url
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
            results[0]["trade"],
            self.trade.id,
        )


    # =========================================
    # CANNOT RETRIEVE ANOTHER USER'S JOURNAL
    # =========================================

    def test_user_cannot_retrieve_another_users_journal(
        self
    ):
        journal = JournalEntry.objects.create(
            trade=self.other_trade,
            notes="Private journal.",
        )

        url = reverse(
            "journal-detail",
            kwargs={
                "pk": journal.id
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
    # UPDATE OWN JOURNAL
    # =========================================

    def test_user_can_update_own_journal(
        self
    ):
        journal = JournalEntry.objects.create(
            trade=self.trade,
            notes="Original notes.",
        )

        url = reverse(
            "journal-detail",
            kwargs={
                "pk": journal.id
            },
        )

        response = self.client.patch(
            url,
            {
                "notes":
                    "Updated journal notes."
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        journal.refresh_from_db()

        self.assertEqual(
            journal.notes,
            "Updated journal notes.",
        )


    # =========================================
    # DELETE OWN JOURNAL
    # =========================================

    def test_user_can_delete_own_journal(
        self
    ):
        journal = JournalEntry.objects.create(
            trade=self.trade,
            notes="Delete me.",
        )

        url = reverse(
            "journal-detail",
            kwargs={
                "pk": journal.id
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
            JournalEntry.objects.filter(
                id=journal.id
            ).exists()
        )