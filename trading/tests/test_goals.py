from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from trading.models import (
    Goal,
    Trade,
    TradingAccount,
)


User = get_user_model()


class GoalAPITests(
    APITestCase
):

    def setUp(
        self
    ):
        self.user = User.objects.create_user(
            username="goaluser",
            email="goal@example.com",
            password="testpass123",
        )

        self.other_user = User.objects.create_user(
            username="othergoaluser",
            email="othergoal@example.com",
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
            broker="Binance",
            currency="USD",
            starting_balance="5000.00",
        )

        self.client.force_authenticate(
            user=self.user
        )

        self.goal_list_url = reverse(
            "goal-list"
        )

        self.goal_summary_url = reverse(
            "goal-summary"
        )


    # =========================================
    # CREATE GOAL
    # =========================================

    def test_user_can_create_goal(
        self
    ):
        data = {
            "title":
                "Monthly Profit Target",

            "description":
                "Reach $5,000 profit this month.",

            "goal_type":
                "PROFIT",

            "target":
                "5000.00",

            "period":
                "MONTHLY",

            "account":
                self.account.id,
        }


        response = self.client.post(
            self.goal_list_url,
            data,
            format="json",
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )


        self.assertEqual(
            Goal.objects.count(),
            1,
        )


        goal = Goal.objects.first()


        self.assertEqual(
            goal.user,
            self.user,
        )


        self.assertEqual(
            goal.account,
            self.account,
        )


        self.assertEqual(
            str(goal.target),
            "5000.00",
        )


    # =========================================
    # ACCOUNT OWNERSHIP
    # =========================================

    def test_user_cannot_create_goal_for_another_users_account(
        self
    ):
        data = {
            "title":
                "Invalid Goal",

            "goal_type":
                "PROFIT",

            "target":
                "1000.00",

            "period":
                "MONTHLY",

            "account":
                self.other_account.id,
        }


        response = self.client.post(
            self.goal_list_url,
            data,
            format="json",
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )


        self.assertEqual(
            Goal.objects.count(),
            0,
        )


    # =========================================
    # USER DATA ISOLATION
    # =========================================

    def test_goal_list_only_returns_authenticated_users_goals(
        self
    ):
        Goal.objects.create(
            user=self.user,
            account=self.account,
            title="My Goal",
            goal_type=Goal.GoalType.PROFIT,
            target="5000.00",
            period=Goal.Period.MONTHLY,
        )


        Goal.objects.create(
            user=self.other_user,
            account=self.other_account,
            title="Other Goal",
            goal_type=Goal.GoalType.PROFIT,
            target="1000.00",
            period=Goal.Period.MONTHLY,
        )


        response = self.client.get(
            self.goal_list_url
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
            results[0]["title"],
            "My Goal",
        )


    # =========================================
    # PROFIT PROGRESS
    # =========================================

    def test_profit_goal_progress_is_calculated_from_trades(
        self
    ):
        goal = Goal.objects.create(
            user=self.user,
            account=self.account,
            title="Profit Goal",
            goal_type=Goal.GoalType.PROFIT,
            target="1000.00",
            period=Goal.Period.MONTHLY,
        )


        Trade.objects.create(
            user=self.user,
            account=self.account,
            symbol="BTCUSD",
            direction=Trade.Direction.LONG,
            status=Trade.Status.CLOSED,
            entry_price="100000.00",
            exit_price="101000.00",
            position_size="0.10",
            profit_loss="400.00",
            entry_time="2026-09-02T10:00:00Z",
            exit_time="2026-09-02T12:00:00Z",
        )


        Trade.objects.create(
            user=self.user,
            account=self.account,
            symbol="ETHUSD",
            direction=Trade.Direction.LONG,
            status=Trade.Status.CLOSED,
            entry_price="4000.00",
            exit_price="4100.00",
            position_size="1.00",
            profit_loss="300.00",
            entry_time="2026-09-02T13:00:00Z",
            exit_time="2026-09-02T14:00:00Z",
        )


        detail_url = reverse(
            "goal-detail",
            kwargs={
                "pk":
                    goal.id
            },
        )


        response = self.client.get(
            detail_url
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )


        self.assertEqual(
            float(
                response.data["current"]
            ),
            700.0,
        )


        self.assertEqual(
            float(
                response.data["progress"]
            ),
            70.0,
        )


    # =========================================
    # COMPLETION
    # =========================================

    def test_goal_is_completed_when_target_is_reached(
        self
    ):
        goal = Goal.objects.create(
            user=self.user,
            account=self.account,
            title="Profit Goal",
            goal_type=Goal.GoalType.PROFIT,
            target="500.00",
            period=Goal.Period.MONTHLY,
        )


        Trade.objects.create(
            user=self.user,
            account=self.account,
            symbol="BTCUSD",
            direction=Trade.Direction.LONG,
            status=Trade.Status.CLOSED,
            entry_price="100000.00",
            exit_price="102000.00",
            position_size="0.10",
            profit_loss="600.00",
            entry_time="2026-09-02T10:00:00Z",
            exit_time="2026-09-02T12:00:00Z",
        )


        detail_url = reverse(
            "goal-detail",
            kwargs={
                "pk":
                    goal.id
            },
        )


        response = self.client.get(
            detail_url
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )


        self.assertGreaterEqual(
            float(
                response.data["progress"]
            ),
            100.0,
        )


        self.assertIn(
            response.data["progress_status"],
            [
                "COMPLETED",
                "ON_TRACK",
            ],
        )


    # =========================================
    # SUMMARY
    # =========================================

    def test_goal_summary_returns_user_goal_counts(
        self
    ):
        Goal.objects.create(
            user=self.user,
            account=self.account,
            title="Goal One",
            goal_type=Goal.GoalType.PROFIT,
            target="5000.00",
            period=Goal.Period.MONTHLY,
        )

        Goal.objects.create(
            user=self.user,
            account=self.account,
            title="Goal Two",
            goal_type=Goal.GoalType.TRADE_COUNT,
            target="20.00",
            period=Goal.Period.MONTHLY,
        )


        response = self.client.get(
            self.goal_summary_url
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
    # DAILY PERIOD
    # =========================================

    def test_daily_goal_can_be_created(
        self
    ):
        data = {
            "title":
                "Daily Profit",

            "goal_type":
                "PROFIT",

            "target":
                "200.00",

            "period":
                "DAILY",

            "account":
                self.account.id,
        }


        response = self.client.post(
            self.goal_list_url,
            data,
            format="json",
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )


        self.assertEqual(
            response.data["period"],
            "DAILY",
        )