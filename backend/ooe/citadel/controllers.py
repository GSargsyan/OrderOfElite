from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from ooe.base.exceptions import OOEException
from ooe.base.events import emit_event, EventTypes
from ooe.citadel.models import CitadelStay
from ooe.citadel.constants import (
    CITADEL_MIN_STAY_MINUTES,
    CITADEL_MAX_STAY_MINUTES,
    CITADEL_REENTRY_COOLDOWN_MINUTES,
    PNG_REENTRY_COOLDOWN_MINUTES,
    PNG_MAX_STAY_MINUTES,
    CITADEL_DEFENSE_MULTIPLIER,
)


class CitadelController:

    @staticmethod
    def get_reentry_cooldown_minutes(user):
        if user.is_persona_non_grata():
            return PNG_REENTRY_COOLDOWN_MINUTES
        return CITADEL_REENTRY_COOLDOWN_MINUTES

    @staticmethod
    def get_max_stay_minutes(user):
        if user.is_persona_non_grata():
            return PNG_MAX_STAY_MINUTES
        return CITADEL_MAX_STAY_MINUTES

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
                timedelta(minutes=CitadelController.get_reentry_cooldown_minutes(user))
            expired_stay.save(update_fields=['left_at', 'cooldown_until'])

            emit_event(EventTypes.LEFT_CITADEL, actor=user, city=user.city)

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
        is_png = user.is_persona_non_grata()

        return {
            'in_citadel': active_stay is not None,
            'entered_at': active_stay.entered_at.timestamp() if active_stay else 0,
            'stay_until': active_stay.scheduled_until.timestamp() if active_stay else 0,
            'cooldown_until': cooldown_until.timestamp() if cooldown_until else 0,
            'min_stay_minutes': CITADEL_MIN_STAY_MINUTES,
            'max_stay_minutes': CitadelController.get_max_stay_minutes(user),
            'cooldown_minutes': CitadelController.get_reentry_cooldown_minutes(user),
            'defense_multiplier': CITADEL_DEFENSE_MULTIPLIER,
            'persona_non_grata': is_png,
            'png_until': user.png_until.timestamp() if is_png and user.png_until else 0,
        }

    @staticmethod
    @transaction.atomic
    def enter(user, minutes):
        from ooe.travel.controllers import TravelController
        from ooe.travel.models import FlightLog
        try:
            minutes = int(minutes)
        except (TypeError, ValueError):
            raise OOEException('Invalid stay duration.')

        if minutes < CITADEL_MIN_STAY_MINUTES:
            raise OOEException('The Citadel does not admit guests for less than '
                f'{CITADEL_MIN_STAY_MINUTES} minutes.')

        max_stay_minutes = CitadelController.get_max_stay_minutes(user)
        if minutes > max_stay_minutes:
            raise OOEException('Sanctuary is granted for at most '
                f'{max_stay_minutes // 60} hours.')

        if CitadelController.get_active_stay(user):
            raise OOEException('You are already within the Citadel walls.')

        cooldown_until = CitadelController.get_cooldown_until(user)
        if cooldown_until:
            raise OOEException('The Citadel doors remain closed to you. '
                'Await the end of your restriction.')

        TravelController.check_and_complete_active_flight(user)
        if FlightLog.objects.filter(user=user, arrived_at__isnull=True).exists():
            raise OOEException('Sanctuary cannot be sought mid-flight.')

        # Entering the Citadel disrupts any party mission the user is part
        # of - same policy as traveling.
        from ooe.missions.controllers import fail_or_cancel_party_missions_for
        fail_or_cancel_party_missions_for(user)

        now = timezone.now()
        CitadelStay.objects.create(
            user=user,
            entered_at=now,
            scheduled_until=now + timedelta(minutes=minutes),
        )

        emit_event(EventTypes.ENTERED_CITADEL, actor=user, city=user.city)

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
            timedelta(minutes=CitadelController.get_reentry_cooldown_minutes(user))
        active_stay.save(update_fields=['left_at', 'cooldown_until'])

        emit_event(EventTypes.LEFT_CITADEL, actor=user, city=user.city)

        return CitadelController.get_tab_data(user)
