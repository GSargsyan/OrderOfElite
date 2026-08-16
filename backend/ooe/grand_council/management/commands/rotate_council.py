from django.core.management.base import BaseCommand

from ooe.grand_council.engine import run_weekly_rotation


class Command(BaseCommand):
    help = ('Manually runs the Grand Council weekly rotation: reshuffles the '
            'roster, resyncs the council chat room, and discards any Order of '
            'Elite draft that has not finished the approval flow. Normally '
            'fires automatically every Monday 00:00 UTC via Celery beat.')

    def handle(self, *args, **options):
        result = run_weekly_rotation()
        self.stdout.write(self.style.SUCCESS(
            f"Rotation complete - term #{result['term_id']}, "
            f"{result['member_count']} member(s) seated."
        ))
