import json

from django.core.management.base import BaseCommand

from ooe.seals.models import SealCompileLog


class Command(BaseCommand):
    help = ('Shows recent Seal compilation attempts (player conditions, '
            'LLM outcome). Use --failed to review rejected requests.')

    def add_arguments(self, parser):
        parser.add_argument('--failed', action='store_true',
                            help='Only show failed compilations')
        parser.add_argument('--limit', type=int, default=20,
                            help='Number of rows to show (default 20)')
        parser.add_argument('--full', action='store_true',
                            help='Also print the raw LLM response')

    def handle(self, *args, **options):
        qs = SealCompileLog.objects.select_related('user')
        if options['failed']:
            qs = qs.filter(success=False)

        rows = list(qs[:options['limit']])
        if not rows:
            self.stdout.write('No compile attempts recorded.')
            return

        for row in rows:
            outcome = 'OK' if row.success else f'FAILED ({row.reason_code})'
            self.stdout.write('=' * 70)
            self.stdout.write(
                f'#{row.id}  {row.created_at:%Y-%m-%d %H:%M:%S}  '
                f'{row.user.username} -> {row.counterparty_username}  '
                f'[{outcome}]  {row.latency_ms}ms  {row.model}')
            self.stdout.write(f'  text: {row.raw_text}')
            if row.success and row.clauses is not None:
                for clause in row.clauses:
                    self.stdout.write(
                        f"  clause: {clause['obligor']} | "
                        f"{clause['trigger']['predicate']}"
                        f"{json.dumps(clause['trigger']['args'])} -> "
                        f"{clause['obligation']['predicate']}"
                        f"{json.dumps(clause['obligation']['args'])}")
            if (options['full'] or not row.success) and row.response_raw:
                self.stdout.write(f'  response: {row.response_raw[:1000]}')
