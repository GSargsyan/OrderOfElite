from django.core.cache import cache
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from ooe.base.exceptions import OOEException
from ooe.users.models import User
from ooe.seals.models import Seal, SealClause
from ooe.seals.compiler import compile_seal_text, render_seal
from ooe.seals.engine import activate_seal
from ooe.seals.constants import (
    SEAL_RAW_TEXT_MAX_LEN,
    SEAL_DEADLINE_MIN_DAYS,
    SEAL_DEADLINE_MAX_DAYS,
    SEAL_COMPILE_RATE_LIMIT,
    SEAL_MAX_PENDING_SENT,
    SEAL_MAX_ACTIVE_PER_USER,
    PNG_PENALTY_DAYS_CHOICES,
    SEAL_HELP_TEXT,
)


class SealsController:

    # ── Read ─────────────────────────────────────────────────

    @staticmethod
    def _serialize(seal, viewer):
        return {
            'id': seal.id,
            'creator': seal.creator.username,
            'counterparty': seal.counterparty.username,
            'is_creator': seal.creator_id == viewer.id,
            'raw_text': seal.raw_text,
            'rendered_text': seal.rendered_text,
            'deadline_days': seal.deadline_days,
            'penalty_png_days': seal.penalty_png_days,
            'status': seal.status,
            'annul_requested_by': (seal.annul_requested_by.username
                                   if seal.annul_requested_by else None),
            'created_at': seal.created_at.timestamp(),
            'signed_at': seal.signed_at.timestamp() if seal.signed_at else 0,
            'resolved_at': seal.resolved_at.timestamp() if seal.resolved_at else 0,
            'clauses': [{
                'obligor': (seal.creator.username if c.obligor == 'party_a'
                            else seal.counterparty.username),
                'status': c.status,
                'deadline_at': c.deadline_at.timestamp() if c.deadline_at else 0,
            } for c in seal.clauses.all()],
        }

    @staticmethod
    def get_tab_data(user):
        base_qs = Seal.objects.filter(
            Q(creator=user) | Q(counterparty=user)
        ).select_related('creator', 'counterparty', 'annul_requested_by') \
         .prefetch_related('clauses')

        incoming = base_qs.filter(
            counterparty=user, status=Seal.PENDING_SIGNATURE)
        outgoing = base_qs.filter(
            creator=user, status=Seal.PENDING_SIGNATURE)
        active = base_qs.filter(status=Seal.ACTIVE)
        history = base_qs.filter(status__in=Seal.RESOLVED_STATUSES)[:20]

        return {
            'incoming': [SealsController._serialize(s, user) for s in incoming],
            'outgoing': [SealsController._serialize(s, user) for s in outgoing],
            'active': [SealsController._serialize(s, user) for s in active],
            'history': [SealsController._serialize(s, user) for s in history],
            'help_text': SEAL_HELP_TEXT,
            'raw_text_max_len': SEAL_RAW_TEXT_MAX_LEN,
            'deadline_min_days': SEAL_DEADLINE_MIN_DAYS,
            'deadline_max_days': SEAL_DEADLINE_MAX_DAYS,
            'penalty_choices': PNG_PENALTY_DAYS_CHOICES,
        }

    # ── Create / preview ─────────────────────────────────────

    @staticmethod
    def compile_preview(user, counterparty_username, raw_text,
                        deadline_days, penalty_png_days):
        raw_text = (raw_text or '').strip()
        if not raw_text:
            raise OOEException('State the terms of the Seal.')
        if len(raw_text) > SEAL_RAW_TEXT_MAX_LEN:
            raise OOEException('The terms must fit within '
                f'{SEAL_RAW_TEXT_MAX_LEN} characters.')

        try:
            deadline_days = int(deadline_days)
        except (TypeError, ValueError):
            raise OOEException('State the deadline in days.')
        if not (SEAL_DEADLINE_MIN_DAYS <= deadline_days <= SEAL_DEADLINE_MAX_DAYS):
            raise OOEException(f'The deadline must be between '
                f'{SEAL_DEADLINE_MIN_DAYS} and {SEAL_DEADLINE_MAX_DAYS} days.')

        try:
            penalty_png_days = int(penalty_png_days)
        except (TypeError, ValueError):
            raise OOEException('Choose a penalty.')
        if penalty_png_days not in PNG_PENALTY_DAYS_CHOICES:
            raise OOEException('Choose a penalty from the offered terms.')

        try:
            counterparty = User.objects.get(username=counterparty_username)
        except User.DoesNotExist:
            raise OOEException('No such Elite is known to the Order.')

        if counterparty.id == user.id:
            raise OOEException('A Seal binds two parties. You cannot seal '
                'a promise with yourself.')

        SealsController._check_caps(user)

        # Rate-limit compilations
        rate_key = f'user_{user.id}_seal_compiles'
        compile_count = cache.get(rate_key) or 0
        if compile_count >= SEAL_COMPILE_RATE_LIMIT:
            raise OOEException('The scribes require rest. Return within the hour.')
        cache.set(rate_key, compile_count + 1, timeout=3600)

        # Discard any previous unsent draft toward this or another party
        Seal.objects.filter(creator=user, status=Seal.DRAFT).delete()

        clauses = compile_seal_text(user, counterparty, raw_text)
        rendered = render_seal(user, counterparty, clauses,
                               deadline_days, penalty_png_days)

        with transaction.atomic():
            seal = Seal.objects.create(
                creator=user,
                counterparty=counterparty,
                raw_text=raw_text,
                compiled={'clauses': clauses},
                rendered_text=rendered,
                deadline_days=deadline_days,
                penalty_png_days=penalty_png_days,
                status=Seal.DRAFT,
            )
            for clause in clauses:
                SealClause.objects.create(
                    seal=seal,
                    obligor=clause['obligor'],
                    trigger=clause['trigger'],
                    obligation=clause['obligation'],
                    deadline_days=deadline_days,
                )

        return {
            'seal_id': seal.id,
            'raw_text': raw_text,
            'rendered_text': rendered,
            'deadline_days': deadline_days,
            'penalty_png_days': penalty_png_days,
            'counterparty': counterparty.username,
        }

    @staticmethod
    def _check_caps(user):
        pending_sent = Seal.objects.filter(
            creator=user, status=Seal.PENDING_SIGNATURE).count()
        if pending_sent >= SEAL_MAX_PENDING_SENT:
            raise OOEException('Too many Seals await signatures. '
                'Withdraw one or await a response.')

        active_count = Seal.objects.filter(
            Q(creator=user) | Q(counterparty=user),
            status=Seal.ACTIVE).count()
        if active_count >= SEAL_MAX_ACTIVE_PER_USER:
            raise OOEException('You are bound by too many Seals already.')

    # ── State transitions ────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def send(user, seal_id):
        try:
            seal = Seal.objects.select_for_update().get(
                id=seal_id, creator=user, status=Seal.DRAFT)
        except Seal.DoesNotExist:
            raise OOEException('This Seal is no longer at hand. Draft it anew.')

        SealsController._check_caps(user)

        seal.status = Seal.PENDING_SIGNATURE
        seal.save(update_fields=['status'])

        return {'status': 'success',
                'message': f'The Seal has been presented to {seal.counterparty.username}.'}

    @staticmethod
    @transaction.atomic
    def discard_draft(user, seal_id):
        Seal.objects.filter(id=seal_id, creator=user, status=Seal.DRAFT).delete()
        return {'status': 'success', 'message': 'The draft has been discarded.'}

    @staticmethod
    @transaction.atomic
    def withdraw(user, seal_id):
        try:
            seal = Seal.objects.select_for_update().get(
                id=seal_id, creator=user, status=Seal.PENDING_SIGNATURE)
        except Seal.DoesNotExist:
            raise OOEException('This Seal cannot be withdrawn.')

        seal.status = Seal.WITHDRAWN
        seal.resolved_at = timezone.now()
        seal.save(update_fields=['status', 'resolved_at'])

        return {'status': 'success', 'message': 'The Seal has been withdrawn.'}

    @staticmethod
    @transaction.atomic
    def sign(user, seal_id):
        try:
            seal = Seal.objects.select_for_update().get(
                id=seal_id, counterparty=user, status=Seal.PENDING_SIGNATURE)
        except Seal.DoesNotExist:
            raise OOEException('This Seal is not yours to sign, '
                'or it is no longer offered.')

        SealsController._check_caps(user)

        seal.status = Seal.ACTIVE
        seal.signed_at = timezone.now()
        seal.save(update_fields=['status', 'signed_at'])

        activate_seal(seal)

        return {'status': 'success',
                'message': 'The Seal is bound. Honor it.'}

    @staticmethod
    @transaction.atomic
    def decline(user, seal_id):
        try:
            seal = Seal.objects.select_for_update().get(
                id=seal_id, counterparty=user, status=Seal.PENDING_SIGNATURE)
        except Seal.DoesNotExist:
            raise OOEException('This Seal is no longer offered.')

        seal.status = Seal.DECLINED
        seal.resolved_at = timezone.now()
        seal.save(update_fields=['status', 'resolved_at'])

        return {'status': 'success', 'message': 'The Seal has been declined.'}

    @staticmethod
    @transaction.atomic
    def annul(user, seal_id):
        """
        Mutual annulment: one party requests, the other confirms.
        """
        try:
            seal = Seal.objects.select_for_update().select_related(
                'creator', 'counterparty', 'annul_requested_by').get(
                Q(creator=user) | Q(counterparty=user),
                id=seal_id, status=Seal.ACTIVE)
        except Seal.DoesNotExist:
            raise OOEException('No such binding Seal.')

        if seal.annul_requested_by is None:
            seal.annul_requested_by = user
            seal.save(update_fields=['annul_requested_by'])
            return {'status': 'success',
                    'message': 'Annulment requested. The Seal remains bound '
                               'until the other party consents.'}

        if seal.annul_requested_by_id == user.id:
            raise OOEException('You have already requested annulment.')

        seal.status = Seal.ANNULLED
        seal.resolved_at = timezone.now()
        seal.save(update_fields=['status', 'resolved_at'])

        now = timezone.now()
        for clause in seal.clauses.filter(
                status__in=[SealClause.WAITING_TRIGGER, SealClause.ARMED]):
            clause.status = SealClause.LAPSED
            clause.resolved_at = now
            clause.save(update_fields=['status', 'resolved_at'])
            clause.index_rows.all().delete()

        return {'status': 'success',
                'message': 'The Seal has been annulled by mutual consent.'}
