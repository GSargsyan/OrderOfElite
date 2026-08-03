import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from ooe.users.models import User
from ooe.seals.models import Seal, SealClause, SealTriggerIndex, PersonaNonGrataLog
from ooe.seals.constants import (
    TRIGGER_PREDICATES,
    OBLIGATION_PREDICATES,
    NEGATIVE_OBLIGATIONS,
    SEAL_TRIGGER_WINDOW_DAYS,
    SEAL_SIGNATURE_EXPIRY_HOURS,
    SEAL_DRAFT_EXPIRY_HOURS,
)

logger = logging.getLogger('django')


# ── Matching ─────────────────────────────────────────────────

def _event_matches_args(predicate, args, event):
    """
    Checks the predicate's non-party args against a GameEvent.
    The party itself was already matched by the SealTriggerIndex lookup.
    """
    meta = event.metadata or {}

    if predicate in ('TRAVELED_TO_CITY', 'TRAVEL_TO', 'AVOID_CITY'):
        return event.city is not None and event.city.name == args.get('city')

    if predicate in ('ENTERED_CITADEL', 'LEFT_CITADEL'):
        return True

    if predicate in ('ITEM_BOUGHT', 'ITEM_SOLD', 'BUY_ITEM', 'SELL_ITEM'):
        if meta.get('item_type') != args.get('item_type'):
            return False
        wanted_key = args.get('item_key')
        return wanted_key is None or meta.get('item_key') == wanted_key

    if predicate in ('SKILL_REACHED', 'REACH_SKILL'):
        return (meta.get('skill') == args.get('skill')
                and (meta.get('points_after') or 0) >= args.get('points', 0))

    return False


def _skill_already_reached(user, args):
    field = f"{args.get('skill')}_points"
    user.refresh_from_db(fields=[field])
    return getattr(user, field, 0) >= args.get('points', 0)


# ── Clause lifecycle ─────────────────────────────────────────

def arm_clause(clause, now=None):
    """
    waiting_trigger -> armed. Sets the obligation deadline, swaps the
    trigger index row for an obligation index row, and immediately
    resolves state-based obligations that are already satisfied.
    """
    now = now or timezone.now()

    clause.status = SealClause.ARMED
    clause.armed_at = now
    clause.deadline_at = now + timedelta(days=clause.deadline_days)
    clause.save(update_fields=['status', 'armed_at', 'deadline_at'])

    clause.index_rows.all().delete()

    obligation = clause.obligation
    obligor_user = clause.seal.user_of(clause.obligor)

    # Already-satisfied state-based obligation: fulfilled on the spot.
    if obligation['predicate'] == 'REACH_SKILL' \
            and _skill_already_reached(obligor_user, obligation['args']):
        fulfill_clause(clause, now)
        return

    SealTriggerIndex.objects.create(
        clause=clause,
        kind=SealTriggerIndex.OBLIGATION,
        event_type=OBLIGATION_PREDICATES[obligation['predicate']],
        user=obligor_user,
    )


def fulfill_clause(clause, now=None):
    now = now or timezone.now()
    clause.status = SealClause.FULFILLED
    clause.resolved_at = now
    clause.save(update_fields=['status', 'resolved_at'])
    clause.index_rows.all().delete()

    _resolve_seal_if_done(clause.seal)


def breach_clause(clause, now=None):
    now = now or timezone.now()
    clause.status = SealClause.BREACHED
    clause.resolved_at = now
    clause.save(update_fields=['status', 'resolved_at'])
    clause.index_rows.all().delete()

    seal = clause.seal
    _apply_penalty(seal, clause, now)

    seal.status = Seal.BREACHED
    seal.resolved_at = now
    seal.save(update_fields=['status', 'resolved_at'])

    # A breached seal is settled; remaining clauses lapse.
    for other in seal.clauses.filter(
            status__in=[SealClause.WAITING_TRIGGER, SealClause.ARMED]):
        other.status = SealClause.LAPSED
        other.resolved_at = now
        other.save(update_fields=['status', 'resolved_at'])
        other.index_rows.all().delete()


def lapse_clause(clause, now=None):
    now = now or timezone.now()
    clause.status = SealClause.LAPSED
    clause.resolved_at = now
    clause.save(update_fields=['status', 'resolved_at'])
    clause.index_rows.all().delete()

    _resolve_seal_if_done(clause.seal)


def _resolve_seal_if_done(seal):
    if seal.status != Seal.ACTIVE:
        return

    unresolved = seal.clauses.filter(
        status__in=[SealClause.WAITING_TRIGGER, SealClause.ARMED]).exists()
    if unresolved:
        return

    if seal.clauses.filter(status=SealClause.BREACHED).exists():
        return  # handled by breach_clause

    seal.status = Seal.FULFILLED
    seal.resolved_at = timezone.now()
    seal.save(update_fields=['status', 'resolved_at'])


def _apply_penalty(seal, clause, now):
    obligor = seal.user_of(clause.obligor)
    days = seal.penalty_png_days

    # Stacks on an already-active persona non grata status.
    base = obligor.png_until if obligor.is_persona_non_grata() else now
    obligor.png_until = base + timedelta(days=days)
    obligor.seal_breaker = True
    obligor.save(update_fields=['png_until', 'seal_breaker'])

    PersonaNonGrataLog.objects.create(
        user=obligor,
        seal=seal,
        days=days,
        reason=f'Breach of Seal #{seal.id}',
    )

    logger.warning('Seal #%s breached by user %s: persona non grata %s days',
                   seal.id, obligor.username, days)


# ── Sign-time setup ──────────────────────────────────────────

def activate_seal(seal):
    """
    Called when the counterparty signs. Sets up every clause:
    IMMEDIATE arms now, TIME_REACHED gets a fire time for the beat task,
    event triggers get index rows.
    """
    now = timezone.now()

    for clause in seal.clauses.all():
        predicate = clause.trigger['predicate']
        args = clause.trigger['args']

        if predicate == 'IMMEDIATE':
            arm_clause(clause, now)
        elif predicate == 'TIME_REACHED':
            clause.trigger_at = now + timedelta(days=args['days'])
            clause.save(update_fields=['trigger_at'])
        else:
            SealTriggerIndex.objects.create(
                clause=clause,
                kind=SealTriggerIndex.TRIGGER,
                event_type=TRIGGER_PREDICATES[predicate],
                user=seal.user_of(args['party']),
            )


# ── Event processing ─────────────────────────────────────────

def process_event(event):
    """
    Matches one GameEvent against the trigger index. One indexed query,
    never a scan over all seals.
    """
    rows = SealTriggerIndex.objects.filter(
        event_type=event.event_type,
        user=event.actor,
    ).select_related('clause', 'clause__seal', 'clause__seal__creator',
                     'clause__seal__counterparty')

    for row in rows:
        clause = row.clause
        if clause.seal.status != Seal.ACTIVE:
            continue

        with transaction.atomic():
            clause = SealClause.objects.select_for_update().get(id=clause.id)
            clause.seal = row.clause.seal  # keep prefetched relations

            if row.kind == SealTriggerIndex.TRIGGER:
                if clause.status != SealClause.WAITING_TRIGGER:
                    continue
                if _event_matches_args(
                        clause.trigger['predicate'],
                        clause.trigger['args'], event):
                    arm_clause(clause)

            else:  # obligation
                if clause.status != SealClause.ARMED:
                    continue
                predicate = clause.obligation['predicate']
                if not _event_matches_args(
                        predicate, clause.obligation['args'], event):
                    continue

                if predicate in NEGATIVE_OBLIGATIONS:
                    breach_clause(clause)
                else:
                    fulfill_clause(clause)


# ── Periodic sweep (celery beat) ─────────────────────────────

def sweep_deadlines():
    now = timezone.now()

    # 1. Arm TIME_REACHED clauses that are due
    due = SealClause.objects.filter(
        status=SealClause.WAITING_TRIGGER,
        trigger_at__isnull=False,
        trigger_at__lte=now,
        seal__status=Seal.ACTIVE,
    ).select_related('seal', 'seal__creator', 'seal__counterparty')
    for clause in due:
        with transaction.atomic():
            locked = SealClause.objects.select_for_update().get(id=clause.id)
            if locked.status == SealClause.WAITING_TRIGGER:
                locked.seal = clause.seal
                arm_clause(locked, now)

    # 2. Resolve armed clauses past their obligation deadline
    overdue = SealClause.objects.filter(
        status=SealClause.ARMED,
        deadline_at__lte=now,
        seal__status=Seal.ACTIVE,
    ).select_related('seal', 'seal__creator', 'seal__counterparty')
    for clause in overdue:
        with transaction.atomic():
            locked = SealClause.objects.select_for_update().get(id=clause.id)
            if locked.status != SealClause.ARMED:
                continue
            locked.seal = clause.seal

            predicate = locked.obligation['predicate']
            if predicate in NEGATIVE_OBLIGATIONS:
                # Survived the window without the forbidden action
                fulfill_clause(locked, now)
            elif predicate == 'REACH_SKILL' and _skill_already_reached(
                    locked.seal.user_of(locked.obligor),
                    locked.obligation['args']):
                fulfill_clause(locked, now)
            else:
                breach_clause(locked, now)

    # 3. Lapse clauses whose trigger never fired within the window
    window_start = now - timedelta(days=SEAL_TRIGGER_WINDOW_DAYS)
    stale = SealClause.objects.filter(
        status=SealClause.WAITING_TRIGGER,
        trigger_at__isnull=True,
        seal__status=Seal.ACTIVE,
        seal__signed_at__lte=window_start,
    ).select_related('seal')
    for clause in stale:
        with transaction.atomic():
            locked = SealClause.objects.select_for_update().get(id=clause.id)
            if locked.status == SealClause.WAITING_TRIGGER:
                locked.seal = clause.seal
                lapse_clause(locked, now)

    # 4. Expire unsigned seals
    signature_cutoff = now - timedelta(hours=SEAL_SIGNATURE_EXPIRY_HOURS)
    Seal.objects.filter(
        status=Seal.PENDING_SIGNATURE,
        created_at__lte=signature_cutoff,
    ).update(status=Seal.EXPIRED, resolved_at=now)

    # 5. Discard abandoned drafts
    draft_cutoff = now - timedelta(hours=SEAL_DRAFT_EXPIRY_HOURS)
    Seal.objects.filter(
        status=Seal.DRAFT,
        created_at__lte=draft_cutoff,
    ).delete()
