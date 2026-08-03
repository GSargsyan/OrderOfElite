from celery import shared_task


@shared_task
def process_game_event(event_id: int):
    """
    Fired after a GameEvent commits. Matches the event against active
    Seal clauses (indexed lookup, deterministic - no LLM involvement).
    """
    from ooe.base.models import GameEvent
    from ooe.seals.engine import process_event

    try:
        event = GameEvent.objects.select_related('actor', 'city').get(id=event_id)
    except GameEvent.DoesNotExist:
        return

    process_event(event)


@shared_task
def check_seal_deadlines():
    """
    Celery beat: arms timed triggers, breaches overdue obligations,
    lapses never-fired triggers, expires unsigned seals.
    """
    from ooe.seals.engine import sweep_deadlines
    sweep_deadlines()
