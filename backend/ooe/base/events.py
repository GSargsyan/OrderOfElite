from django.db import transaction


class EventTypes:
    TRAVELED_TO_CITY = 'traveled_to_city'
    ENTERED_CITADEL = 'entered_citadel'
    LEFT_CITADEL = 'left_citadel'
    ITEM_BOUGHT = 'item_bought'
    ITEM_SOLD = 'item_sold'
    SKILL_TRAINED = 'skill_trained'
    PLAYER_KILLED = 'player_killed'
    # Future: 'money_sent', 'mission_completed', ...


def emit_event(event_type, actor, target=None, city=None, metadata=None):
    """
    Records a GameEvent row inside the caller's transaction, then defers
    Seal processing to after commit so a rolled-back action can never
    arm or fulfill a Seal clause.

    Call from controller code that is already inside transaction.atomic().
    """
    from ooe.base.models import GameEvent

    event = GameEvent.objects.create(
        event_type=event_type,
        actor=actor,
        target=target,
        city=city,
        metadata=metadata or {},
    )

    def _dispatch():
        from ooe.seals.tasks import process_game_event
        process_game_event.delay(event.id)

    transaction.on_commit(_dispatch)

    return event
