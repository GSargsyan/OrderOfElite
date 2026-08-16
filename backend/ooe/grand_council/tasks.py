from celery import shared_task


@shared_task
def rotate_grand_council():
    """
    Celery beat, every Monday 00:00 UTC: full reshuffle of the Grand
    Council roster, chat room membership resync, and discard of any
    Order of Elite draft that hasn't finished the approval flow.
    """
    from ooe.grand_council.engine import run_weekly_rotation
    run_weekly_rotation()
