import json
from datetime import timedelta

import redis
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from ooe.users.models import User
from ooe.base.exceptions import OOEException
from ooe.base.events import emit_event, EventTypes
from ooe.assassination.models import SearchRecord, Kill
from ooe.assassination import combat
from ooe.assassination.constants import (
    SEARCH_COST_CITY,
    SEARCH_COST_GLOBAL,
    SEARCH_DURATION_MINUTES,
    SEARCH_VALIDITY_MINUTES,
    ATTACK_COOLDOWN_SUCCESS_HOURS,
    ATTACK_COOLDOWN_FAIL_HOURS,
    KILL_LOOT_PERCENT,
)

redis_client = redis.Redis(host='redis', port=6379, db=0)


class AssassinationController:
    def __init__(self, user: User):
        self.user = user

    def get_search_history(self):
        records = SearchRecord.objects.filter(searcher=self.user).select_related('target')[:50]
        now = timezone.now()

        history = []
        for record in records:
            ready = record.ready_at <= now
            entry = {
                'id': record.id,
                'target': record.target.username,
                'search_type': record.search_type,
                'cost': record.cost,
                'created_at': record.created_at.timestamp(),
                'ready_at': record.ready_at.timestamp(),
                'ready': ready,
            }
            if ready:
                entry['found'] = record.found
                entry['searcher_city'] = record.searcher_city_name
                entry['result_city'] = record.result_city_name
                entry['result_status'] = record.result_status
            history.append(entry)

        return history

    def initiate_search(self, target_username: str, search_type: str):
        from ooe.citadel.controllers import CitadelController
        from ooe.travel.models import FlightLog

        if search_type not in (SearchRecord.CITY, SearchRecord.GLOBAL):
            raise OOEException('Invalid search type')

        target_username = (target_username or '').strip()
        if not target_username:
            raise OOEException('Enter a target name')

        target = User.objects.filter(username__iexact=target_username).first()
        if target is None:
            raise OOEException('No Elite found by that name')

        if target.id == self.user.id:
            raise OOEException('You cannot search yourself')

        cost = SEARCH_COST_CITY if search_type == SearchRecord.CITY else SEARCH_COST_GLOBAL

        searcher = User.objects.select_for_update().get(id=self.user.id)
        if searcher.elite_coins < cost:
            raise OOEException('Not enough Elite Coins')

        # Resolve the target's status snapshot. Travel here isn't
        # hyper-realistic: target.city stays the origin city for the whole
        # flight and only flips on arrival, so it's always well-defined —
        # a flying target is reported in their origin city, flagged as
        # currently in flight, destination withheld.
        in_flight = FlightLog.objects.filter(user=target, arrived_at__isnull=True).exists()
        in_citadel = CitadelController.get_active_stay(target) is not None

        if in_flight:
            status = SearchRecord.STATUS_FLIGHT
        elif in_citadel:
            status = SearchRecord.STATUS_CITADEL
        else:
            status = SearchRecord.STATUS_REGULAR
        city_name = target.city.name

        if search_type == SearchRecord.GLOBAL:
            found = True
            result_city_name = city_name
            result_status = status
        else:
            found = target.city_id == searcher.city_id
            result_city_name = city_name if found else None
            result_status = status if found else None

        User.objects.filter(id=searcher.id).update(elite_coins=F('elite_coins') - cost)

        SearchRecord.objects.create(
            searcher=searcher,
            target=target,
            search_type=search_type,
            cost=cost,
            ready_at=timezone.now() + timedelta(minutes=SEARCH_DURATION_MINUTES),
            searcher_city_name=searcher.city.name,
            found=found,
            result_city_name=result_city_name,
            result_status=result_status,
        )

        return {'status': 'success'}

    def _has_valid_search(self, target):
        """A resolved, successful search on this target within the last
        SEARCH_VALIDITY_MINUTES since it became ready."""
        validity_cutoff = timezone.now() - timedelta(minutes=SEARCH_VALIDITY_MINUTES)
        return SearchRecord.objects.filter(
            searcher=self.user,
            target=target,
            found=True,
            ready_at__lte=timezone.now(),
            ready_at__gte=validity_cutoff,
        ).exists()

    def _cooldown_until(self):
        """When this user is next free to attack, or None if not on
        cooldown. Same rule attempt_assassination() enforces, factored out
        so the panel can show it before the player even tries."""
        last_attack = Kill.objects.filter(attacker=self.user).order_by('-created_at').first()
        if not last_attack:
            return None

        target_died = last_attack.outcome in (Kill.KILL, Kill.MUTUAL)
        cooldown_hours = ATTACK_COOLDOWN_SUCCESS_HOURS if target_died else ATTACK_COOLDOWN_FAIL_HOURS
        until = last_attack.created_at + timedelta(hours=cooldown_hours)

        return until if until > timezone.now() else None

    def get_attack_panel_data(self, target_username: str):
        """Equipped gear names for both sides, shown to the attacker before
        committing — informational only, already folded into the combat
        math via effective stats."""
        from ooe.items.constants import GUNS, CARS

        def equipped_names(u):
            gun = u.guns.filter(is_equipped=True).first()
            car = u.cars.filter(city=u.city, is_equipped=True).first()
            return {
                'gun': GUNS.get(gun.gun, {}).get('name') if gun else None,
                'car': CARS.get(car.car, {}).get('name') if car else None,
            }

        cooldown_until = self._cooldown_until()

        data = {
            'attacker': equipped_names(self.user),
            'target': None,
            'has_valid_search': False,
            'search_expires_at': None,
            'cooldown_until': cooldown_until.timestamp() if cooldown_until else None,
        }

        target_username = (target_username or '').strip()
        if not target_username:
            return data

        target = User.objects.filter(username__iexact=target_username).first()
        if target is None or target.id == self.user.id:
            return data

        validity_cutoff = timezone.now() - timedelta(minutes=SEARCH_VALIDITY_MINUTES)
        valid_search = SearchRecord.objects.filter(
            searcher=self.user, target=target, found=True,
            ready_at__lte=timezone.now(), ready_at__gte=validity_cutoff,
        ).order_by('-ready_at').first()

        if valid_search:
            data['has_valid_search'] = True
            data['search_expires_at'] = (
                valid_search.ready_at + timedelta(minutes=SEARCH_VALIDITY_MINUTES)
            ).timestamp()
            data['target'] = {
                **equipped_names(target),
                'is_dead': target.is_dead(),
            }

        return data

    def attempt_assassination(self, target_username: str, budget, attack_type: str):
        from ooe.travel.controllers import TravelController
        from ooe.travel.models import FlightLog

        attacker = self.user

        if attacker.is_dead():
            raise OOEException('The deceased cannot conduct operations')

        if attack_type not in combat.ATTACK_TYPES:
            raise OOEException('Invalid attack type')

        try:
            budget = int(budget)
        except (TypeError, ValueError):
            raise OOEException('Enter a valid operational budget')

        if budget <= 0:
            raise OOEException('Enter an operational budget')

        TravelController.check_and_complete_active_flight(attacker)
        if FlightLog.objects.filter(user=attacker, arrived_at__isnull=True).exists():
            raise OOEException('You cannot conduct operations while in flight')

        target_username = (target_username or '').strip()
        if not target_username:
            raise OOEException('Enter a target name')

        target = User.objects.filter(username__iexact=target_username).first()
        if target is None:
            raise OOEException('No Elite found by that name')

        if target.id == attacker.id:
            raise OOEException('You cannot target yourself')

        if target.is_dead():
            raise OOEException('This operative is already deceased')

        TravelController.check_and_complete_active_flight(target)
        if FlightLog.objects.filter(user=target, arrived_at__isnull=True).exists():
            raise OOEException('The target is currently in flight')

        if target.city_id != attacker.city_id:
            raise OOEException('The target is not in your city')

        if not self._has_valid_search(target):
            raise OOEException('You must locate this target before engaging — conduct a search first')

        cooldown_until = self._cooldown_until()
        if cooldown_until:
            remaining_minutes = int((cooldown_until - timezone.now()).total_seconds() // 60)
            hours, minutes = divmod(remaining_minutes, 60)
            raise OOEException(
                f'You are still recovering from your last operation. '
                f'Available again in {hours}h {minutes}m'
            )

        with transaction.atomic():
            attacker = User.objects.select_for_update().get(id=attacker.id)
            target = User.objects.select_for_update().get(id=target.id)

            if budget > attacker.money_cash:
                raise OOEException('Not enough cash to commit to this budget')

            attacker_stats = attacker.get_effective_stats()
            defender_stats = target.get_effective_stats()

            attacker_gun = attacker.guns.filter(is_equipped=True).first()
            attacker_car = attacker.cars.filter(city=attacker.city, is_equipped=True).first()
            defender_gun = target.guns.filter(is_equipped=True).first()
            defender_car = target.cars.filter(city=target.city, is_equipped=True).first()

            result = combat.resolve_attack(
                attacker={
                    'rank': attacker.rank,
                    'skill': attacker_stats['attack'],
                    'hp': attacker.health,
                    'budget': budget,
                },
                defender={
                    'rank': target.rank,
                    'skill': defender_stats['defense'],
                    'hp': target.health,
                },
                attack_type=attack_type,
            )

            attacker_health_before = attacker.health
            defender_health_before = target.health

            defender_died = result['outcome'] in (combat.KILL, combat.MUTUAL)
            attacker_died = result['outcome'] in (combat.BACKFIRE, combat.MUTUAL)

            attacker.money_cash -= budget

            money_looted = 0
            if result['outcome'] == combat.KILL:
                money_looted = int(target.money_cash * KILL_LOOT_PERCENT)
                attacker.money_cash += money_looted
                target.money_cash -= money_looted

            if defender_died:
                attacker.kills += 1

            attacker.health = 0 if attacker_died else result['attacker_hp_after']
            target.health = 0 if defender_died else result['defender_hp_after']

            attacker.save(update_fields=['money_cash', 'health', 'kills'])
            target.save(update_fields=['money_cash', 'health'])

            Kill.objects.create(
                attacker=attacker,
                defender=target,
                attack_type=attack_type,
                budget=budget,
                city=attacker.city,
                attacker_gun=attacker_gun.gun if attacker_gun else '',
                attacker_car=attacker_car.car if attacker_car else '',
                defender_gun=defender_gun.gun if defender_gun else '',
                defender_car=defender_car.car if defender_car else '',
                attacker_health_before=attacker_health_before,
                attacker_health_after=attacker.health,
                defender_health_before=defender_health_before,
                defender_health_after=target.health,
                outcome=result['outcome'],
                money_looted=money_looted,
            )

            if defender_died:
                self._process_death(target)
                emit_event(EventTypes.PLAYER_KILLED, actor=attacker, target=target, city=attacker.city, metadata={
                    'attack_type': attack_type,
                    'outcome': result['outcome'],
                })
            if attacker_died:
                self._process_death(attacker)
                emit_event(EventTypes.PLAYER_KILLED, actor=target, target=attacker, city=target.city, metadata={
                    'attack_type': attack_type,
                    'outcome': result['outcome'],
                })

        if defender_died:
            redis_client.publish(f'player_eliminated:{target.id}', json.dumps({
                'killed_by': attacker.username,
            }))
        if attacker_died:
            redis_client.publish(f'player_eliminated:{attacker.id}', json.dumps({
                'killed_by': target.username,
            }))

        return {
            'outcome': result['outcome'],
            'attacker_health': attacker.health,
            'defender_health': target.health,
            'target_eliminated': defender_died,
            'you_were_eliminated': attacker_died,
            'money_looted': money_looted,
        }

    @staticmethod
    def _process_death(user):
        """
        Runs once, at the moment a player is confirmed dead. Permadeath —
        this row never comes back to life; a future 'boost the new
        account' feature creates a fresh User row instead of reviving
        this one.

        Wiped (mutable, live-progress state): items, Black Market progress,
        uncollected stash, non-DM chat membership, in-flight Extraction
        missions, in-play Seals. Kept: money_cash/money_bank (reserved for
        a future inheritance feature), DM history, every historical log
        (Kill rows, transactions, GameEvents) — those are records, not
        live state, and other players' history depends on them too.
        """
        from ooe.items.models import UserGun, UserCar, UserHouse, UserAirplane
        from ooe.black_market.models import PlayerDrugState
        from ooe.chat.models import ChatRoom
        from ooe.missions.models import ExtractionMission
        from ooe.seals.models import Seal

        user.died_at = timezone.now()
        user.save(update_fields=['died_at'])

        UserGun.objects.filter(user=user).delete()
        UserCar.objects.filter(user=user).delete()
        UserHouse.objects.filter(user=user).delete()
        UserAirplane.objects.filter(user=user).delete()

        PlayerDrugState.objects.filter(user=user).delete()

        for room in ChatRoom.objects.filter(users=user).exclude(chat_type='direct'):
            room.users.remove(user)

        ExtractionMission.objects.filter(
            Q(initiator=user, status__in=ExtractionMission.ACTIVE_STATUSES) |
            Q(driver=user, status__in=ExtractionMission.JOINED_STATUSES)
        ).update(status=ExtractionMission.CANCELLED, updated_at=timezone.now())

        Seal.objects.filter(
            Q(creator=user) | Q(counterparty=user),
            status__in=Seal.ACTIVE_STATUSES,
        ).update(status=Seal.OBSOLETED, resolved_at=timezone.now())
