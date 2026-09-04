import io

from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from trading.models import (
    Trade,
    TradingAccount,
)


User = get_user_model()


class TradeImportTests(
    APITestCase
):

    def setUp(
        self
    ):
        self.user = User.objects.create_user(
            username="importuser",
            email="import@example.com",
            password="testpass123",
        )

        self.account = TradingAccount.objects.create(
            user=self.user,
            name="Import Account",
            broker="Binance",
            currency="USD",
            starting_balance="10000.00",
        )

        self.client.force_authenticate(
            user=self.user
        )

        self.csv_url = reverse(
            "trade-import-trades"
        )

        self.json_url = reverse(
            "trade-import-json"
        )


    # =========================================
    # CSV SUCCESS
    # =========================================

    def test_csv_import_creates_trades(
        self
    ):
        csv_content = (
            "symbol,direction,status,entry_price,"
            "exit_price,position_size,risk_amount,"
            "profit_loss,fees,entry_time,exit_time,"
            "stop_loss,take_profit,external_trade_id\n"
            "BTCUSD,LONG,CLOSED,100000,102000,"
            "0.10,100,200,5,"
            "2026-09-02T10:00:00Z,"
            "2026-09-02T13:00:00Z,"
            "99000,102000,CSV-BTC-001\n"
        )

        file = io.BytesIO(
            csv_content.encode(
                "utf-8"
            )
        )

        file.name = "trades.csv"


        response = self.client.post(
            self.csv_url,
            {
                "account":
                    self.account.id,

                "file":
                    file,
            },
            format="multipart",
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )


        self.assertEqual(
            Trade.objects.count(),
            1,
        )


        trade = Trade.objects.first()


        self.assertEqual(
            trade.source,
            Trade.Source.IMPORT,
        )


        self.assertEqual(
            trade.external_trade_id,
            "CSV-BTC-001",
        )


    # =========================================
    # CSV DUPLICATE
    # =========================================

    def test_csv_duplicate_is_skipped(
        self
    ):
        Trade.objects.create(
            user=self.user,
            account=self.account,
            symbol="BTCUSD",
            direction="LONG",
            status="CLOSED",
            entry_price="100000.00",
            exit_price="102000.00",
            position_size="0.10",
            entry_time="2026-09-02T10:00:00Z",
            exit_time="2026-09-02T13:00:00Z",
            source=Trade.Source.IMPORT,
            external_trade_id="CSV-DUP-001",
        )


        csv_content = (
            "symbol,direction,status,entry_price,"
            "exit_price,position_size,entry_time,"
            "exit_time,external_trade_id\n"
            "BTCUSD,LONG,CLOSED,100000,102000,"
            "0.10,"
            "2026-09-02T10:00:00Z,"
            "2026-09-02T13:00:00Z,"
            "CSV-DUP-001\n"
        )


        file = io.BytesIO(
            csv_content.encode(
                "utf-8"
            )
        )

        file.name = "trades.csv"


        response = self.client.post(
            self.csv_url,
            {
                "account":
                    self.account.id,

                "file":
                    file,
            },
            format="multipart",
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )


        self.assertEqual(
            Trade.objects.count(),
            1,
        )


        self.assertEqual(
            response.data["created"],
            0,
        )


        self.assertEqual(
            len(
                response.data[
                    "duplicates"
                ]
            ),
            1,
        )


    # =========================================
    # CSV INVALID DATA
    # =========================================

    def test_csv_invalid_direction_is_rejected(
        self
    ):
        csv_content = (
            "symbol,direction,status,entry_price,"
            "position_size,entry_time\n"
            "BTCUSD,SIDEWAYS,OPEN,100000,"
            "0.10,"
            "2026-09-02T10:00:00Z\n"
        )


        file = io.BytesIO(
            csv_content.encode(
                "utf-8"
            )
        )

        file.name = "trades.csv"


        response = self.client.post(
            self.csv_url,
            {
                "account":
                    self.account.id,

                "file":
                    file,
            },
            format="multipart",
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
    # JSON SUCCESS
    # =========================================

    def test_json_import_creates_trade(
        self
    ):
        data = {
            "account":
                self.account.id,

            "trades": [
                {
                    "symbol":
                        "ETHUSD",

                    "direction":
                        "SHORT",

                    "status":
                        "CLOSED",

                    "entry_price":
                        "4200",

                    "exit_price":
                        "4100",

                    "position_size":
                        "1",

                    "risk_amount":
                        "100",

                    "profit_loss":
                        "100",

                    "fees":
                        "3",

                    "entry_time":
                        "2026-09-02T10:00:00Z",

                    "exit_time":
                        "2026-09-02T12:00:00Z",

                    "external_trade_id":
                        "JSON-ETH-001",
                }
            ],
        }


        response = self.client.post(
            self.json_url,
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
            Trade.Source.IMPORT,
        )


        self.assertEqual(
            trade.external_trade_id,
            "JSON-ETH-001",
        )


    # =========================================
    # JSON DUPLICATE
    # =========================================

    def test_json_duplicate_is_skipped(
        self
    ):
        Trade.objects.create(
            user=self.user,
            account=self.account,
            symbol="ETHUSD",
            direction="SHORT",
            status="CLOSED",
            entry_price="4200.00",
            exit_price="4100.00",
            position_size="1.00",
            entry_time="2026-09-02T10:00:00Z",
            exit_time="2026-09-02T12:00:00Z",
            source=Trade.Source.IMPORT,
            external_trade_id="JSON-DUP-001",
        )


        data = {
            "account":
                self.account.id,

            "trades": [
                {
                    "symbol":
                        "ETHUSD",

                    "direction":
                        "SHORT",

                    "status":
                        "CLOSED",

                    "entry_price":
                        "4200",

                    "exit_price":
                        "4100",

                    "position_size":
                        "1",

                    "entry_time":
                        "2026-09-02T10:00:00Z",

                    "exit_time":
                        "2026-09-02T12:00:00Z",

                    "external_trade_id":
                        "JSON-DUP-001",
                }
            ],
        }


        response = self.client.post(
            self.json_url,
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


        self.assertEqual(
            response.data["created"],
            0,
        )


        self.assertEqual(
            len(
                response.data[
                    "duplicates"
                ]
            ),
            1,
        )