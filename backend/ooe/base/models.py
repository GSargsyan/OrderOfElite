from django.db import models


class GameEvent(models.Model):
    """
    Unified append-only log of player actions.

    Every gameplay controller records its domain action here in addition
    to its own specific table (which stays the source of truth for its
    feature). Seals predicate checks, and any future system that needs
    to ask "what did this player do", read this single table.

    event_type values are defined in ooe.base.events.EventTypes.
    """
    event_type = models.CharField(max_length=40)
    actor = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='game_events',
    )
    target = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='targeted_game_events',
        null=True,
        blank=True,
    )
    city = models.ForeignKey(
        'cities.City',
        on_delete=models.CASCADE,
        related_name='game_events',
        null=True,
        blank=True,
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ooe_game_events'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['event_type', 'actor', 'created_at']),
            models.Index(fields=['actor', 'created_at']),
        ]
