from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from trading.services.journal_reminders import check_journal_reminders


User = get_user_model()


class Command(BaseCommand):
    help = "Check for closed trades that need journal reminders."

    def handle(self, *args, **options):
        users = User.objects.all()

        total_reminders = 0

        for user in users:
            notifications = check_journal_reminders(user)

            total_reminders += len(notifications)

        self.stdout.write(
            self.style.SUCCESS(
                f"Journal reminder check completed. "
                f"{total_reminders} eligible reminder(s) processed."
            )
        )