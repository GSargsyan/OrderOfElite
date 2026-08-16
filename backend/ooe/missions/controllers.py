import time
import random
from datetime import timedelta

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from django.db.models import F

from ooe.users.models import User
from ooe.items.models import UserCar, UserGun
from ooe.items.constants import CARS, GUNS
from ooe.base.exceptions import OOEException
from ooe.base.constants import RANK_EXPS
from ooe.missions.constants import \
    RANK_REQUIREMENTS, \
    MISSIONS, \
    SIMPLE_MISSIONS, \
    PARTY_MISSIONS, \
    MISSION_RESOLUTION_SECONDS
from ooe.missions.models import PartyMission, MissionParticipant

ITEM_CATALOGS = {'car': CARS, 'gun': GUNS}


class MissionsController:
    def __init__(self, user: object):
        self.user = user

    def get_missions_tab_data(self):
        return {
            'stakeout': Mission('stakeout', self.user).get_tab_data(),
            'recon_op': Mission('recon_op', self.user).get_tab_data(),
            'exfiltration': PartyMissionController('exfiltration', self.user).get_tab_data(),
            'hvt': PartyMissionController('hvt', self.user).get_tab_data(),
        }


class Mission:
    def __init__(self, name: str, user: object):
        self.name = name
        self.user = user

    def validate_start(self):
        if self.name not in SIMPLE_MISSIONS:
            raise OOEException('Invalid mission')

        cd_remaining = cache.get(f'user_{self.user.id}_{self.name}_cd')

        if cd_remaining is not None and cd_remaining > int(time.time()):
            raise OOEException('Mission is on cooldown')

        if RANK_REQUIREMENTS[self.name] > self.user.rank:
            raise OOEException('Rank is too low')

    def get_tab_data(self):
        return {
            'allowed': self.user.rank >= RANK_REQUIREMENTS[self.name],
            'cd_remaining': cache.get(f'user_{self.user.id}_{self.name}_cd') or 0,
        }

    def generate_reward(self):
        abs_exp_diff = RANK_EXPS[MISSIONS[self.name]['max_reward_rank']] - RANK_EXPS[RANK_REQUIREMENTS[self.name]]
        exp_passed = self.user.exp - RANK_EXPS[RANK_REQUIREMENTS[self.name]]
        progress = (exp_passed / abs_exp_diff)
        reward_range_diff = MISSIONS[self.name]['max_reward'] - MISSIONS[self.name]['min_reward']

        reward_range_progress = int(reward_range_diff * progress)

        lower_bound_rank = MISSIONS[self.name]['min_reward'] + reward_range_progress
        lower_bound_max = MISSIONS[self.name]['max_reward'] - MISSIONS[self.name]['random_range']
        min_reward = min(lower_bound_rank, lower_bound_max)

        # $0 reward is not allowed
        min_reward = max(min_reward, 1)
        max_reward_mission = MISSIONS[self.name]['max_reward']

        max_reward = min(max_reward_mission, min_reward + MISSIONS[self.name]['random_range'])

        return random.randint(min_reward, max_reward)

    def start(self):
        # TODO: log missions in mission log
        self.validate_start()

        reward = self.generate_reward()
        exp_reward = MISSIONS[self.name]['exp_reward']
        # update experience
        User.objects.filter(id=self.user.id).update(money_cash=F('money_cash') + reward)
        self.user.add_exp(exp_reward)


        cd = int(time.time()) + MISSIONS[self.name]['cooldown']

        cache.set(f'user_{self.user.id}_{self.name}_cd',
            cd,
            timeout = MISSIONS[self.name]['cooldown'])

        return {'reward': reward,
                'exp_reward': exp_reward,
                'cd_remaining': cd}


def generate_party_mission_reward(mission_type):
    """Flat reward for missions with one, a random range for the rest —
    no rank-progress scaling yet (that's the future skill-based rework)."""
    config = PARTY_MISSIONS[mission_type]
    if 'reward' in config:
        return config['reward']
    return random.randint(config['min_reward'], config['max_reward'])


def fail_or_cancel_party_missions_for(user):
    """
    Called wherever a participant's continued participation becomes
    impossible mid-mission: death, traveling away, or entering the
    Citadel. A mission still assembling in its Lobby is simply cancelled —
    same as before this feature existed, nothing was risked yet. A mission
    already IN_PROGRESS FAILS outright for every participant: an operation
    already underway doesn't survive losing one of its people, and
    everyone still in it is notified. A mission that's already RESOLVED
    (timer elapsed, reward computed) is left alone — it already concluded.
    """
    from ooe.notifications.controllers import push

    mission_ids = list(MissionParticipant.objects.filter(
        user=user,
        mission__status__in=PartyMission.DISRUPTIBLE_STATUSES,
    ).values_list('mission_id', flat=True))

    if not mission_ids:
        return

    PartyMission.objects.filter(id__in=mission_ids, status=PartyMission.LOBBY).update(
        status=PartyMission.CANCELLED, updated_at=timezone.now())

    in_progress = list(PartyMission.objects.filter(id__in=mission_ids, status=PartyMission.IN_PROGRESS))
    PartyMission.objects.filter(id__in=[m.id for m in in_progress]).update(
        status=PartyMission.FAILED, resolved_at=timezone.now(), updated_at=timezone.now())

    for mission in in_progress:
        mission_name = PARTY_MISSIONS[mission.mission_type]['name']
        others = MissionParticipant.objects.filter(mission=mission).exclude(user=user).select_related('user')
        for participant in others:
            push(
                participant.user,
                'party_mission_failed',
                f'{mission_name} failed — a participant is no longer available.',
                payload={'mission_id': mission.id, 'mission_type': mission.mission_type},
            )


class PartyMissionController:
    """
    Shared lobby -> ready -> start -> resolve -> claim state machine for
    every multiplayer mission (Exfiltration, High-Profile Target
    Operation). Which roles exist, how many slots each has, and what kind
    of item fills them lives in PARTY_MISSIONS[mission_type] — nothing in
    here is specific to one mission type.
    """
    def __init__(self, mission_type: str, user: object):
        if mission_type not in PARTY_MISSIONS:
            raise OOEException('Invalid mission type')

        self.mission_type = mission_type
        self.config = PARTY_MISSIONS[mission_type]
        self.user = user

    # ── cooldown ──────────────────────────────────────────────
    def cd_key(self, user_id):
        return f'user_{user_id}_{self.mission_type}_cd'

    def get_cd_remaining(self, user_id):
        return cache.get(self.cd_key(user_id)) or 0

    def invite_expiry_cutoff(self):
        return timezone.now() - timedelta(seconds=self.config['invite_ttl'])

    # ── role bookkeeping ─────────────────────────────────────
    def open_role_slots(self, mission):
        """{role: open_slot_count} for every role that still has room,
        counting any participant that isn't rejected/expired against
        that role's slot total."""
        filled = {}
        for p in mission.participants.exclude(invite_status__in=(MissionParticipant.REJECTED, MissionParticipant.EXPIRED)):
            if p.role != MissionParticipant.INITIATOR:
                filled[p.role] = filled.get(p.role, 0) + 1

        return {
            role: cfg['slots'] - filled.get(role, 0)
            for role, cfg in self.config['roles'].items()
            if filled.get(role, 0) < cfg['slots']
        }

    def is_ready_to_start(self, mission):
        if self.open_role_slots(mission):
            return False

        non_initiator = mission.participants.exclude(role=MissionParticipant.INITIATOR).exclude(
            invite_status__in=(MissionParticipant.REJECTED, MissionParticipant.EXPIRED))

        return non_initiator.exists() and not non_initiator.exclude(invite_status=MissionParticipant.READY).exists()

    # ── lookups ───────────────────────────────────────────────
    def get_active_participation(self):
        """This user's row on a currently active mission of this type, if
        any. A pending invite they haven't accepted yet doesn't count —
        invitations are just offers, they don't tie you down."""
        return MissionParticipant.objects.filter(
            user=self.user,
            mission__mission_type=self.mission_type,
            mission__status__in=PartyMission.ACTIVE_STATUSES,
        ).exclude(invite_status=MissionParticipant.INVITED).select_related('mission').first()

    def get_invitations(self):
        """Pending invitations to this user for this mission type. Only
        visible while the Initiator is in the same city — keeps their
        location secret otherwise, same rule as before."""
        participants = MissionParticipant.objects.filter(
            user=self.user,
            invite_status=MissionParticipant.INVITED,
            mission__mission_type=self.mission_type,
            mission__status=PartyMission.LOBBY,
            invited_at__gte=self.invite_expiry_cutoff(),
            mission__initiator__city=self.user.city,
        ).select_related('mission', 'mission__initiator').order_by('invited_at')

        ttl = self.config['invite_ttl']

        return [{
            'id': p.id,
            'mission_id': p.mission_id,
            'initiator': p.mission.initiator.username,
            'role': p.role,
            'expires_at': (p.invited_at + timedelta(seconds=ttl)).timestamp(),
        } for p in participants]

    def get_available_items(self, item_type):
        if item_type == 'car':
            owned = set(UserCar.objects.filter(user=self.user, city=self.user.city).values_list('car', flat=True))
        else:
            owned = set(UserGun.objects.filter(user=self.user).values_list('gun', flat=True))

        catalog = ITEM_CATALOGS[item_type]
        return [{'key': key, 'name': catalog[key]['name']} for key in catalog if key in owned]

    def serialize_mission(self, mission):
        participants = list(mission.participants.select_related('user').order_by('id'))
        my_participant = next((p for p in participants if p.user_id == self.user.id), None)

        my_item_type = None
        if my_participant and my_participant.role != MissionParticipant.INITIATOR:
            my_item_type = self.config['roles'][my_participant.role]['item_type']

        def item_name(participant):
            if not participant.equipped_item:
                return None
            item_type = self.config['roles'].get(participant.role, {}).get('item_type')
            return ITEM_CATALOGS.get(item_type, {}).get(participant.equipped_item, {}).get('name')

        return {
            'id': mission.id,
            'mission_type': mission.mission_type,
            'status': mission.status,
            'resolves_at': mission.resolves_at.timestamp() if mission.resolves_at else None,
            'reward': mission.reward,
            'exp_reward': mission.exp_reward,
            'my_role': my_participant.role if my_participant else None,
            'my_invite_status': my_participant.invite_status if my_participant else None,
            'my_claimed': bool(my_participant.claimed_at) if my_participant else False,
            'my_item_type': my_item_type,
            'open_roles': self.open_role_slots(mission) if mission.status == PartyMission.LOBBY else {},
            'participants': [{
                'role': p.role,
                'username': p.user.username,
                'invite_status': p.invite_status,
                'item_name': item_name(p),
                'is_me': p.user_id == self.user.id,
            } for p in participants],
        }

    def get_tab_data(self):
        allowed = self.user.rank >= RANK_REQUIREMENTS[self.mission_type]
        cd_remaining = self.get_cd_remaining(self.user.id)

        data = {
            'allowed': allowed,
            'cd_remaining': cd_remaining,
            'mode': 'idle',
            'invitations': [],
            'mission': None,
            'cars': [],
            'guns': [],
            'roles': {role: cfg['slots'] for role, cfg in self.config['roles'].items()},
        }

        if not allowed:
            return data

        participation = self.get_active_participation()
        if participation is not None:
            mission = participation.mission
            data['mode'] = mission.status
            data['mission'] = self.serialize_mission(mission)

            if mission.status == PartyMission.LOBBY and \
                    participation.role != MissionParticipant.INITIATOR and \
                    participation.invite_status == MissionParticipant.ACCEPTED:
                item_type = self.config['roles'][participation.role]['item_type']
                data['cars' if item_type == 'car' else 'guns'] = self.get_available_items(item_type)
        elif cd_remaining <= int(time.time()):
            data['invitations'] = self.get_invitations()

        return data

    # ── actions ───────────────────────────────────────────────
    @transaction.atomic
    def invite(self, role: str, username: str):
        if role not in self.config['roles']:
            raise OOEException('Invalid role')

        if self.user.rank < RANK_REQUIREMENTS[self.mission_type]:
            raise OOEException('Rank is too low')

        cd_remaining = cache.get(self.cd_key(self.user.id))
        if cd_remaining is not None and cd_remaining > int(time.time()):
            raise OOEException('Mission is on cooldown')

        username = (username or '').strip()
        if not username:
            raise OOEException('Enter a username to invite')

        target = User.objects.filter(username__iexact=username).first()
        if target is None:
            raise OOEException('No Elite found by that name')

        if target.id == self.user.id:
            raise OOEException('You cannot invite yourself')

        if target.rank < RANK_REQUIREMENTS[self.mission_type]:
            raise OOEException('That Elite has not reached the required rank')

        participation = self.get_active_participation()

        if participation is not None and participation.mission.initiator_id != self.user.id:
            raise OOEException(f'You are already part of a {self.config["name"]} operation')

        if participation is None:
            # the Initiator's own row exists purely so get_active_participation()
            # and the roster can find them — it never needs accepting/readying
            mission = PartyMission.objects.create(
                mission_type=self.mission_type,
                initiator=self.user,
                city=self.user.city,
            )
            MissionParticipant.objects.create(
                mission=mission,
                user=self.user,
                role=MissionParticipant.INITIATOR,
                invite_status=MissionParticipant.READY,
                responded_at=timezone.now(),
            )
        else:
            mission = participation.mission
            if mission.status != PartyMission.LOBBY:
                raise OOEException('This operation has already started')

        if MissionParticipant.objects.filter(mission=mission, user=target).exists():
            raise OOEException('That Elite has already been invited to this operation')

        if self.open_role_slots(mission).get(role, 0) <= 0:
            raise OOEException('No open slots for that role')

        # No checks on the target's city, cooldown or current mission —
        # that would leak info about them. The invitation simply hangs
        # unseen until it expires.
        MissionParticipant.objects.create(
            mission=mission,
            user=target,
            role=role,
        )

        return {'status': 'success'}

    @transaction.atomic
    def accept(self, mission_id):
        participant = MissionParticipant.objects.select_for_update(of=('self',)).select_related(
            'mission', 'mission__initiator'
        ).filter(
            mission_id=mission_id,
            user=self.user,
            invite_status=MissionParticipant.INVITED,
        ).first()

        if participant is None:
            raise OOEException('Invitation is no longer available')

        mission = participant.mission
        if mission.status != PartyMission.LOBBY or \
                participant.invited_at < self.invite_expiry_cutoff() or \
                mission.initiator.city_id != self.user.city_id:
            raise OOEException('Invitation is no longer available')

        if self.user.rank < RANK_REQUIREMENTS[self.mission_type]:
            raise OOEException('Rank is too low')

        cd_remaining = cache.get(self.cd_key(self.user.id))
        if cd_remaining is not None and cd_remaining > int(time.time()):
            raise OOEException('Mission is on cooldown')

        existing = self.get_active_participation()
        if existing is not None and existing.mission_id != mission.id:
            raise OOEException(f'You are already part of a {self.config["name"]} operation')

        participant.invite_status = MissionParticipant.ACCEPTED
        participant.responded_at = timezone.now()
        participant.save(update_fields=['invite_status', 'responded_at'])

        return {'status': 'success'}

    @transaction.atomic
    def reject(self, mission_id):
        participant = MissionParticipant.objects.select_for_update(of=('self',)).filter(
            mission_id=mission_id,
            user=self.user,
            invite_status=MissionParticipant.INVITED,
        ).first()

        if participant is None:
            raise OOEException('Invitation is no longer available')

        participant.invite_status = MissionParticipant.REJECTED
        participant.responded_at = timezone.now()
        participant.save(update_fields=['invite_status', 'responded_at'])

        return {'status': 'success'}

    @transaction.atomic
    def ready(self, mission_id, item: str):
        participant = MissionParticipant.objects.select_for_update(of=('self',)).select_related('mission').filter(
            mission_id=mission_id,
            user=self.user,
            invite_status=MissionParticipant.ACCEPTED,
        ).first()

        if participant is None:
            raise OOEException('Mission is no longer available')

        if participant.mission.status != PartyMission.LOBBY:
            raise OOEException('This operation has already started')

        item_type = self.config['roles'][participant.role]['item_type']
        catalog = ITEM_CATALOGS[item_type]

        if item not in catalog:
            raise OOEException('Invalid item')

        if item_type == 'car':
            owns = UserCar.objects.filter(user=self.user, car=item, city=self.user.city).exists()
        else:
            owns = UserGun.objects.filter(user=self.user, gun=item).exists()

        if not owns:
            raise OOEException(f'You do not own that {item_type}')

        participant.equipped_item = item
        participant.invite_status = MissionParticipant.READY
        participant.save(update_fields=['equipped_item', 'invite_status'])

        return {'status': 'success'}

    @transaction.atomic
    def unready(self, mission_id):
        participant = MissionParticipant.objects.select_for_update(of=('self',)).filter(
            mission_id=mission_id,
            user=self.user,
            invite_status=MissionParticipant.READY,
        ).first()

        if participant is None:
            raise OOEException('Mission is no longer available')

        participant.equipped_item = None
        participant.invite_status = MissionParticipant.ACCEPTED
        participant.save(update_fields=['equipped_item', 'invite_status'])

        return {'status': 'success'}

    @transaction.atomic
    def cancel(self, mission_id):
        """Any participant aborts the whole operation while it's still in
        its Lobby — same all-or-nothing rule as before, just extended
        past 2 roles."""
        mission = PartyMission.objects.select_for_update(of=('self',)).filter(
            id=mission_id,
            mission_type=self.mission_type,
            status=PartyMission.LOBBY,
            participants__user=self.user,
        ).first()

        if mission is None:
            raise OOEException('Mission is no longer available')

        mission.status = PartyMission.CANCELLED
        mission.save(update_fields=['status', 'updated_at'])

        return {'status': 'success'}

    def start(self, mission_id):
        missing_item_role_name = None

        with transaction.atomic():
            mission = PartyMission.objects.select_for_update(of=('self',)).filter(
                id=mission_id,
                mission_type=self.mission_type,
                initiator=self.user,
                status=PartyMission.LOBBY,
            ).first()

            if mission is None:
                raise OOEException('Mission is not ready to start')

            if not self.is_ready_to_start(mission):
                raise OOEException('Not everyone is ready yet')

            initiator = User.objects.select_for_update().get(id=mission.initiator_id)

            participants = list(
                MissionParticipant.objects.select_for_update(of=('self',)).select_related('user').filter(
                    mission=mission,
                ).exclude(role=MissionParticipant.INITIATOR).exclude(
                    invite_status__in=(MissionParticipant.REJECTED, MissionParticipant.EXPIRED),
                )
            )

            participant_user_ids = [initiator.id] + [p.user_id for p in participants]

            now_ts = int(time.time())
            for user_id in participant_user_ids:
                cd_remaining = cache.get(self.cd_key(user_id))
                if cd_remaining is not None and cd_remaining > now_ts:
                    raise OOEException('Mission is on cooldown')

            # cities may have changed since anyone accepted, re-check live
            for participant in participants:
                if participant.user.city_id != initiator.city_id:
                    raise OOEException(f'{participant.user.username} is no longer available')

            # consume every participant's chosen gear — all-or-nothing, so
            # look everything up first and only delete once nobody's gear
            # has gone missing since they readied up
            pending_consumption = []
            for participant in participants:
                item_type = self.config['roles'][participant.role]['item_type']

                if item_type == 'car':
                    item_row = UserCar.objects.select_for_update().filter(
                        user=participant.user, car=participant.equipped_item, city_id=initiator.city_id,
                    ).first()
                else:
                    item_row = UserGun.objects.select_for_update().filter(
                        user=participant.user, gun=participant.equipped_item,
                    ).first()

                if item_row is None:
                    # that participant's gear is gone, drop them back to
                    # choosing again and abort this start attempt
                    participant.equipped_item = None
                    participant.invite_status = MissionParticipant.ACCEPTED
                    participant.save(update_fields=['equipped_item', 'invite_status'])
                    missing_item_role_name = participant.role
                    break

                pending_consumption.append((participant.user, item_type, item_row))

            if not missing_item_role_name:
                from ooe.items.controllers import ItemsController
                for user, item_type, item_row in pending_consumption:
                    item_row.delete()
                    if item_type == 'car':
                        ItemsController._auto_equip_best_car(user)
                    else:
                        ItemsController._auto_equip_best_gun(user)

                mission.status = PartyMission.IN_PROGRESS
                mission.started_at = timezone.now()
                mission.resolves_at = mission.started_at + timedelta(seconds=MISSION_RESOLUTION_SECONDS)
                mission.save(update_fields=['status', 'started_at', 'resolves_at', 'updated_at'])

                cooldown = self.config['cooldown']
                cd = now_ts + cooldown
                for user_id in participant_user_ids:
                    cache.set(self.cd_key(user_id), cd, timeout=cooldown)

        # raised outside the transaction so the downgrade above still commits
        if missing_item_role_name:
            raise OOEException(f'A participant no longer owns their chosen {missing_item_role_name} gear')

        return {'status': 'success', 'resolves_at': mission.resolves_at.timestamp()}

    @transaction.atomic
    def claim(self, mission_id):
        participant = MissionParticipant.objects.select_for_update(of=('self',)).select_related('mission').filter(
            mission_id=mission_id,
            user=self.user,
            claimed_at__isnull=True,
        ).first()

        if participant is None:
            raise OOEException('Nothing to claim')

        mission = participant.mission
        if mission.status != PartyMission.RESOLVED:
            raise OOEException('This operation has not concluded yet')

        exp_reward = mission.exp_reward
        reward = mission.reward if participant.role == MissionParticipant.INITIATOR else 0

        if reward:
            User.objects.filter(id=self.user.id).update(money_cash=F('money_cash') + reward)
        self.user.add_exp(exp_reward)

        participant.claimed_at = timezone.now()
        participant.save(update_fields=['claimed_at'])

        if not MissionParticipant.objects.filter(mission=mission, claimed_at__isnull=True).exists():
            mission.status = PartyMission.COMPLETED
            mission.save(update_fields=['status', 'updated_at'])

        return {'status': 'success', 'reward': reward, 'exp_reward': exp_reward}
