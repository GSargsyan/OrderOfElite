from datetime import timedelta

from celery import shared_task
from django.utils import timezone


@shared_task
def expire_party_mission_invitations():
    """
    Marks dangling per-role invitations as expired, freeing that role's
    slot back up. The mission itself stays in its Lobby so the Initiator
    can invite a replacement without losing progress on roles that are
    already accepted or ready.
    """
    from ooe.missions.models import MissionParticipant
    from ooe.missions.constants import PARTY_MISSIONS

    for mission_type, config in PARTY_MISSIONS.items():
        cutoff = timezone.now() - timedelta(seconds=config['invite_ttl'])
        MissionParticipant.objects.filter(
            mission__mission_type=mission_type,
            invite_status=MissionParticipant.INVITED,
            invited_at__lt=cutoff,
        ).update(invite_status=MissionParticipant.EXPIRED)


@shared_task
def resolve_party_missions():
    """
    Flips IN_PROGRESS party missions whose timer has elapsed to RESOLVED,
    computes the reward now (not at Start — the payout isn't known until
    the operation actually concludes), and notifies every participant
    that a Claim is waiting for them.
    """
    from ooe.missions.models import PartyMission, MissionParticipant
    from ooe.missions.constants import PARTY_MISSIONS
    from ooe.missions.controllers import generate_party_mission_reward
    from ooe.notifications.controllers import push

    due = PartyMission.objects.filter(
        status=PartyMission.IN_PROGRESS,
        resolves_at__lte=timezone.now(),
    )

    for mission in due:
        config = PARTY_MISSIONS[mission.mission_type]

        mission.reward = generate_party_mission_reward(mission.mission_type)
        mission.exp_reward = config['exp_reward']
        mission.status = PartyMission.RESOLVED
        mission.resolved_at = timezone.now()
        mission.save(update_fields=['reward', 'exp_reward', 'status', 'resolved_at', 'updated_at'])

        for participant in MissionParticipant.objects.filter(mission=mission).select_related('user'):
            push(
                participant.user,
                'party_mission_resolved',
                f'{config["name"]} complete — your share is ready to claim.',
                payload={'mission_id': mission.id, 'mission_type': mission.mission_type},
            )
