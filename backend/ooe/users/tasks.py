from celery import shared_task


@shared_task
def reset_elite_coins():
    """
    Celery beat task — runs every Monday at 00:00 UTC.

    Resets every player's Elite Coins balance back to the weekly amount.
    This is a reset, not a grant: unspent coins do not carry over.
    """
    from ooe.users.models import User
    from ooe.users.constants import ELITE_COINS_WEEKLY_AMOUNT

    User.objects.all().update(elite_coins=ELITE_COINS_WEEKLY_AMOUNT)
