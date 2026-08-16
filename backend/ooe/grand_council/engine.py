from django.db import transaction
from django.db.models import F
from django.utils import timezone

from ooe.chat.models import ChatRoom
from ooe.users.models import User
from ooe.grand_council.models import (
    CouncilTerm,
    CouncilMembership,
    OrderOfEliteVersion,
)
from ooe.grand_council.constants import (
    COUNCIL_MIN_RANK,
    COUNCIL_SEATS,
    COUNCIL_CHAT_ROOM_NAME,
    COUNCIL_CHAT_ROOM_TYPE,
)


def get_eligible_players():
    """
    Alive, non-guest players at or above the minimum rank, ordered by
    the confirmed selection criteria: rank, then kills, then net worth,
    with a deterministic final tiebreak on id.
    """
    return (
        User.objects
        .filter(died_at__isnull=True, rank__gte=COUNCIL_MIN_RANK)
        .exclude(username__startswith='guest_')
        .annotate(net_worth=F('money_cash') + F('money_bank'))
        .order_by('-rank', '-kills', '-net_worth', 'id')
    )


def run_weekly_rotation(now=None):
    """
    Celery beat, every Monday 00:00 UTC (also runnable manually via the
    `rotate_council` management command): a full reshuffle of the
    Grand Council roster, discard of any Order of Elite draft that
    hasn't finished the approval flow, and resync of the dedicated
    chat room's membership - all in one atomic operation.
    """
    now = now or timezone.now()
    selected = list(get_eligible_players()[:COUNCIL_SEATS])

    with transaction.atomic():
        CouncilTerm.objects.filter(ended_at__isnull=True).update(ended_at=now)
        term = CouncilTerm.objects.create(started_at=now)

        for seat, user in enumerate(selected, start=1):
            CouncilMembership.objects.create(
                term=term,
                user=user,
                seat=seat,
                rank_snapshot=user.rank,
                kills_snapshot=user.kills,
                net_worth_snapshot=user.money_cash + user.money_bank,
            )

        # A draft only lives as long as the council that proposed it.
        OrderOfEliteVersion.objects.filter(
            status__in=OrderOfEliteVersion.OPEN_STATUSES
        ).update(status=OrderOfEliteVersion.DISCARDED, resolved_at=now)

        room, _ = ChatRoom.objects.get_or_create(
            chat_type=COUNCIL_CHAT_ROOM_TYPE,
            defaults={'name': COUNCIL_CHAT_ROOM_NAME},
        )
        room.users.set(selected)

    return {'term_id': term.id, 'member_count': len(selected)}
