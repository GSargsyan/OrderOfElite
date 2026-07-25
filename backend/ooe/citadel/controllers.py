from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from ooe.base.exceptions import OOEException
from ooe.citadel.models import CitadelStay
from ooe.citadel.constants import (
    CITADEL_MIN_STAY_MINUTES,
    CITADEL_MAX_STAY_MINUTES,
    CITADEL_REENTRY_COOLDOWN_MINUTES,
    CITADEL_DEFENSE_MULTIPLIER,
)


class CitadelController:

    @staticmethod
    def check_and_complete_expired_stay(user):
        """
        Completes a stay whose scheduled time has passed but was never
        marked as left. Deterministic regardless of when it runs: the
        leave time is the scheduled end, not the observation time.
        """
        expired_stay = CitadelStay.objects.filter(
            user=user,
            left_at__isnull=True,
            scheduled_until__lte=timezone.now(),
        ).first()
        if expired_stay:
            expired_stay.left_at = expired_stay.scheduled_until
            expired_stay.cooldown_until = expired_stay.scheduled_until + \
                timedelta(minutes=CITADEL_REENTRY_COOLDOWN_MINUTES)
            expired_stay.save(update_fields=['left_at', 'cooldown_until'])

    @staticmethod
    def get_active_stay(user):
        CitadelController.check_and_complete_expired_stay(user)

        return CitadelStay.objects.filter(
            user=user,
            left_at__isnull=True,
        ).first()

    @staticmethod
    def get_stat_multipliers(user):
        """
        Modifier source for User.get_effective_stats().
        Returns per-stat multipliers granted by the Citadel.
        """
        if CitadelController.get_active_stay(user):
            return {'defense': CITADEL_DEFENSE_MULTIPLIER}

        return {}

    @staticmethod
    def get_cooldown_until(user):
        """Returns the reentry cooldown end as datetime, or None."""
        latest_stay = CitadelStay.objects.filter(
            user=user,
            left_at__isnull=False,
        ).order_by('-left_at').first()

        if latest_stay and latest_stay.cooldown_until \
                and latest_stay.cooldown_until > timezone.now():
            return latest_stay.cooldown_until

        return None

    @staticmethod
    def get_tab_data(user):
        active_stay = CitadelController.get_active_stay(user)
        cooldown_until = CitadelController.get_cooldown_until(user)

        return {
            'in_citadel': active_stay is not None,
            'entered_at': active_stay.entered_at.timestamp() if active_stay else 0,
            'stay_until': active_stay.scheduled_until.timestamp() if active_stay else 0,
            'cooldown_until': cooldown_until.timestamp() if cooldown_until else 0,
            'min_stay_minutes': CITADEL_MIN_STAY_MINUTES,
            'max_stay_minutes': CITADEL_MAX_STAY_MINUTES,
            'cooldown_minutes': CITADEL_REENTRY_COOLDOWN_MINUTES,
            'defense_multiplier': CITADEL_DEFENSE_MULTIPLIER,
        }

    @staticmethod
    @transaction.atomic
    def enter(user, minutes):
        from ooe.travel.controllers import TravelController
        from ooe.travel.models import FlightLog
        from ooe.missions.models import ExtractionMission

        try:
            minutes = int(minutes)
        except (TypeError, ValueError):
            raise OOEException('Invalid stay duration.')

        if minutes < CITADEL_MIN_STAY_MINUTES:
            raise OOEException('The Citadel does not admit guests for less than '
                f'{CITADEL_MIN_STAY_MINUTES} minutes.')

        if minutes > CITADEL_MAX_STAY_MINUTES:
            raise OOEException('Sanctuary is granted for at most '
                f'{CITADEL_MAX_STAY_MINUTES // 60} hours.')

        if CitadelController.get_active_stay(user):
            raise OOEException('You are already within the Citadel walls.')

        cooldown_until = CitadelController.get_cooldown_until(user)
        if cooldown_until:
            raise OOEException('The Citadel doors remain closed to you. '
                'Await the end of your restriction.')

        TravelController.check_and_complete_active_flight(user)
        if FlightLog.objects.filter(user=user, arrived_at__isnull=True).exists():
            raise OOEException('Sanctuary cannot be sought mid-flight.')

        # Entering the Citadel abandons any Extraction mission the user is
        # part of - same policy as traveling.
        ExtractionMission.objects.filter(
            Q(initiator=user, status__in=ExtractionMission.ACTIVE_STATUSES) |
            Q(driver=user, status__in=ExtractionMission.JOINED_STATUSES)
        ).update(status=ExtractionMission.CANCELLED, updated_at=timezone.now())

        now = timezone.now()
        CitadelStay.objects.create(
            user=user,
            entered_at=now,
            scheduled_until=now + timedelta(minutes=minutes),
        )

        return CitadelController.get_tab_data(user)

    @staticmethod
    @transaction.atomic
    def leave(user):
        active_stay = CitadelController.get_active_stay(user)
        if not active_stay:
            raise OOEException('You are not within the Citadel walls.')

        now = timezone.now()
        active_stay.left_at = now
        active_stay.cooldown_until = now + \
            timedelta(minutes=CITADEL_REENTRY_COOLDOWN_MINUTES)
        active_stay.save(update_fields=['left_at', 'cooldown_until'])

        return CitadelController.get_tab_data(user)
