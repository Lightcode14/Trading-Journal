from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from trading.models import (
    Strategy,
)


User = get_user_model()


class StrategyAPITests(
    APITestCase
):

    def setUp(
        self
    ):
        self.user = User.objects.create_user(
            username="strategyuser",
            email="strategy@example.com",
            password="testpass123",
        )

        self.other_user = User.objects.create_user(
            username="otherstrategyuser",
            email="otherstrategy@example.com",
            password="testpass123",
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

        self.strategy_list_url = reverse(
            "strategy-list"
        )


    # =========================================
    # CREATE STRATEGY
    # =========================================

    def test_user_can_create_strategy(
        self
    ):
        data = {
            "name":
                "Trend Following",

            "description":
                "Follow strong market trends.",
        }


        response = self.client.post(
            self.strategy_list_url,
            data,
            format="json",
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )


        self.assertEqual(
            Strategy.objects.count(),
            3,
        )


        strategy = Strategy.objects.get(
            name="Trend Following"
        )


        self.assertEqual(
            strategy.user,
            self.user,
        )


    # =========================================
    # USER DATA ISOLATION
    # =========================================

    def test_strategy_list_only_returns_authenticated_users_strategies(
        self
    ):
        response = self.client.get(
            self.strategy_list_url
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
            results[0]["name"],
            "Breakout",
        )


    # =========================================
    # CANNOT RETRIEVE ANOTHER USER'S STRATEGY
    # =========================================

    def test_user_cannot_retrieve_another_users_strategy(
        self
    ):
        url = reverse(
            "strategy-detail",
            kwargs={
                "pk":
                    self.other_strategy.id
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
    # UPDATE OWN STRATEGY
    # =========================================

    def test_user_can_update_own_strategy(
        self
    ):
        url = reverse(
            "strategy-detail",
            kwargs={
                "pk":
                    self.strategy.id
            },
        )


        response = self.client.patch(
            url,
            {
                "name":
                    "Updated Breakout"
            },
            format="json",
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )


        self.strategy.refresh_from_db()


        self.assertEqual(
            self.strategy.name,
            "Updated Breakout",
        )


    # =========================================
    # CANNOT UPDATE ANOTHER USER'S STRATEGY
    # =========================================

    def test_user_cannot_update_another_users_strategy(
        self
    ):
        url = reverse(
            "strategy-detail",
            kwargs={
                "pk":
                    self.other_strategy.id
            },
        )


        response = self.client.patch(
            url,
            {
                "name":
                    "Hacked Strategy"
            },
            format="json",
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )


        self.other_strategy.refresh_from_db()


        self.assertEqual(
            self.other_strategy.name,
            "Scalping",
        )


    # =========================================
    # DELETE OWN STRATEGY
    # =========================================

    def test_user_can_delete_own_strategy(
        self
    ):
        url = reverse(
            "strategy-detail",
            kwargs={
                "pk":
                    self.strategy.id
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
            Strategy.objects.filter(
                id=self.strategy.id
            ).exists()
        )


    # =========================================
    # CANNOT DELETE ANOTHER USER'S STRATEGY
    # =========================================

    def test_user_cannot_delete_another_users_strategy(
        self
    ):
        url = reverse(
            "strategy-detail",
            kwargs={
                "pk":
                    self.other_strategy.id
            },
        )


        response = self.client.delete(
            url
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )


        self.assertTrue(
            Strategy.objects.filter(
                id=self.other_strategy.id
            ).exists()
        )