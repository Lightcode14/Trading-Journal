from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from trading.services.weekly_summary import (
    check_weekly_summary,
)


User = get_user_model()


class Command(BaseCommand):
    help = (
        "Check and create Weekly Summary "
        "notifications for eligible users."
    )

    def handle(self, *args, **options):
        users = User.objects.all()

        processed_users = 0
        skipped_users = 0

        for user in users:
            notification = (
                check_weekly_summary(user)
            )

            if notification is not None:
                processed_users += 1
            else:
                skipped_users += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Weekly Summary check completed. "
                f"{processed_users} eligible user(s) processed. "
                f"{skipped_users} user(s) skipped."
            )
        )