from datetime import timedelta

from django.db.models import F
from django.utils import timezone

from ooe.users.models import User
from ooe.base.exceptions import OOEException
from ooe.assassination.models import SearchRecord
from ooe.assassination.constants import SEARCH_COST_CITY, SEARCH_COST_GLOBAL, SEARCH_DURATION_MINUTES


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
