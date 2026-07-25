from django.db import models


class CitadelStay(models.Model):
    """
    Tracks all Citadel stays, active and historical.

    Active stay:    left_at IS NULL and scheduled_until > now
    Completed stay: left_at IS NOT NULL

    A stay whose scheduled_until has passed but whose left_at is still NULL
    is completed lazily (left_at = scheduled_until), so all state is
    derivable from timestamps no matter when it is observed.

    cooldown_until is set when the stay completes (actual leave time +
    reentry cooldown).
    """
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='citadel_stays',
    )
    entered_at = models.DateTimeField()
    scheduled_until = models.DateTimeField()
    left_at = models.DateTimeField(null=True, blank=True)
    cooldown_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'ooe_citadel_stays'
        ordering = ['-entered_at']
