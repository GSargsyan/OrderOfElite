from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from ooe.base.exceptions import OOEException
from ooe.grand_council.models import (
    CouncilTerm,
    CouncilMembership,
    OrderOfEliteVersion,
    Condition,
    OrderOfEliteApproval,
)
from ooe.grand_council.constants import (
    COUNCIL_APPROVAL_THRESHOLD_CAP,
    PNG_PENALTY_DAYS_CHOICES,
    BLACKLIST_BOUNTY_CHOICES,
    ORDER_OF_ELITE_TITLE,
    CONDITION_TITLE_MAX_LEN,
    CONDITION_CONTENT_MAX_LEN,
)


class GrandCouncilController:

    # ── Read ─────────────────────────────────────────────────

    @staticmethod
    def _serialize_member(membership):
        return {
            'username': membership.user.username,
            'seat': membership.seat,
            'rank': membership.rank_snapshot,
            'kills': membership.kills_snapshot,
            'net_worth': membership.net_worth_snapshot,
        }

    @staticmethod
    def _serialize_condition(condition):
        res = {
            'id': condition.id,
            'order': condition.order,
            'title': condition.title,
            'content': condition.content,
            'condition_type': condition.condition_type,
            'consequence': condition.consequence,
        }
        if condition.consequence == Condition.PERSONA_NON_GRATA:
            res['png_days'] = condition.png_days
        elif condition.consequence == Condition.BLACKLIST:
            res['bounty_amount'] = condition.bounty_amount
        return res

    @staticmethod
    def _serialize_document(version):
        return {
            'title': ORDER_OF_ELITE_TITLE,
            'version_number': version.version_number,
            'published_at': version.published_at.timestamp() if version.published_at else 0,
            'conditions': [GrandCouncilController._serialize_condition(c)
                           for c in version.conditions.all()],
        }

    @staticmethod
    def _serialize_version(version, viewer=None):
        approvals = list(version.approvals.select_related('member').all())
        approvals_count = sum(1 for a in approvals if a.decision == OrderOfEliteApproval.APPROVE)
        rejections_count = sum(1 for a in approvals if a.decision == OrderOfEliteApproval.REJECT)
        viewer_vote = None
        if viewer is not None:
            for a in approvals:
                if a.member_id == viewer.id:
                    viewer_vote = a.decision
                    break

        return {
            'id': version.id,
            'version_number': version.version_number,
            'status': version.status,
            'author': version.author.username if version.author else None,
            'is_author': viewer is not None and version.author_id == getattr(viewer, 'id', None),
            'conditions': [GrandCouncilController._serialize_condition(c)
                           for c in version.conditions.all()],
            'created_at': version.created_at.timestamp(),
            'submitted_at': version.submitted_at.timestamp() if version.submitted_at else 0,
            'approvals_count': approvals_count,
            'rejections_count': rejections_count,
            'peer_threshold': GrandCouncilController._peer_threshold(version.author),
            'viewer_vote': viewer_vote,
        }

    @staticmethod
    def get_current_term():
        return CouncilTerm.objects.filter(ended_at__isnull=True).first()

    @staticmethod
    def get_current_members():
        term = GrandCouncilController.get_current_term()
        if not term:
            return CouncilMembership.objects.none()
        return CouncilMembership.objects.filter(term=term).select_related('user')

    @staticmethod
    def is_current_council_member(user):
        return GrandCouncilController.get_current_members().filter(user=user).exists()

    @staticmethod
    def get_live_version():
        return OrderOfEliteVersion.objects.filter(
            status=OrderOfEliteVersion.PUBLISHED
        ).prefetch_related('conditions').order_by('-published_at').first()

    @staticmethod
    def get_open_version():
        return OrderOfEliteVersion.objects.filter(
            status__in=OrderOfEliteVersion.OPEN_STATUSES
        ).select_related('author').prefetch_related('conditions', 'approvals').first()

    @staticmethod
    def _peer_threshold(author):
        if author is None:
            return 0
        others = GrandCouncilController.get_current_members().exclude(user=author).count()
        return min(COUNCIL_APPROVAL_THRESHOLD_CAP, others)

    @staticmethod
    def get_tab_data(user):
        from ooe.chat.models import ChatRoom
        from ooe.grand_council.constants import COUNCIL_CHAT_ROOM_TYPE

        term = GrandCouncilController.get_current_term()
        members = GrandCouncilController.get_current_members()
        is_member = GrandCouncilController.is_current_council_member(user)
        live_version = GrandCouncilController.get_live_version()
        open_version = GrandCouncilController.get_open_version()

        council_chat_room_id = None
        if is_member:
            room = ChatRoom.objects.filter(chat_type=COUNCIL_CHAT_ROOM_TYPE).first()
            council_chat_room_id = room.id if room else None

        return {
            'council': [GrandCouncilController._serialize_member(m) for m in members],
            'term_started_at': term.started_at.timestamp() if term else 0,
            'is_council_member': is_member,
            'council_chat_room_id': council_chat_room_id,
            'live_document': GrandCouncilController._serialize_document(live_version)
                              if live_version else None,
            'pending_draft': GrandCouncilController._serialize_version(open_version, viewer=user)
                              if (is_member and open_version) else None,
            'order_of_elite_title': ORDER_OF_ELITE_TITLE,
            'condition_type_choices': Condition.TYPE_CHOICES,
            'consequence_choices': Condition.CONSEQUENCE_CHOICES,
            'png_penalty_days_choices': PNG_PENALTY_DAYS_CHOICES,
            'blacklist_bounty_choices': BLACKLIST_BOUNTY_CHOICES,
        }

    # ── Draft authoring ──────────────────────────────────────

    @staticmethod
    def _require_current_member(user):
        if not GrandCouncilController.is_current_council_member(user):
            raise OOEException('This action is reserved for current Grand Council members.')

    @staticmethod
    def _get_draft_for_author(user, version_id):
        GrandCouncilController._require_current_member(user)
        try:
            return OrderOfEliteVersion.objects.select_for_update().get(
                id=version_id, author=user, status=OrderOfEliteVersion.DRAFT)
        except OrderOfEliteVersion.DoesNotExist:
            raise OOEException('No editable draft was found.')

    @staticmethod
    def _clean_condition_fields(title, content, condition_type, consequence, png_days, bounty_amount):
        title = (title or '').strip()
        if not title:
            raise OOEException('State a title for the condition.')
        if len(title) > CONDITION_TITLE_MAX_LEN:
            raise OOEException(f'The title must fit within {CONDITION_TITLE_MAX_LEN} characters.')

        content = (content or '').strip()
        if not content:
            raise OOEException('State the content of the condition.')
        if len(content) > CONDITION_CONTENT_MAX_LEN:
            raise OOEException(f'The content must fit within {CONDITION_CONTENT_MAX_LEN} characters.')

        if condition_type not in dict(Condition.TYPE_CHOICES):
            raise OOEException('Choose a valid condition type.')

        if condition_type == Condition.INFORMATIVE:
            return title, content, condition_type, Condition.NONE, None, None

        # condition_type == RULE
        if consequence not in dict(Condition.CONSEQUENCE_CHOICES):
            raise OOEException('Choose a valid consequence.')

        if consequence == Condition.PERSONA_NON_GRATA:
            try:
                png_days = int(png_days)
            except (TypeError, ValueError):
                raise OOEException('Choose a duration for persona non grata.')
            if png_days not in PNG_PENALTY_DAYS_CHOICES:
                raise OOEException('Choose a duration from the offered terms.')
            bounty_amount = None
        elif consequence == Condition.BLACKLIST:
            try:
                bounty_amount = int(bounty_amount)
            except (TypeError, ValueError):
                raise OOEException('Choose a bounty amount.')
            if bounty_amount not in BLACKLIST_BOUNTY_CHOICES:
                raise OOEException('Choose a bounty amount from the offered terms.')
            png_days = None
        else:
            png_days = None
            bounty_amount = None

        return title, content, condition_type, consequence, png_days, bounty_amount

    @staticmethod
    @transaction.atomic
    def create_draft(user):
        GrandCouncilController._require_current_member(user)

        if OrderOfEliteVersion.objects.filter(
                status__in=OrderOfEliteVersion.OPEN_STATUSES).exists():
            raise OOEException('A version of the Order of Elite is already awaiting review.')

        next_number = (OrderOfEliteVersion.objects.aggregate(
            m=Max('version_number'))['m'] or 0) + 1

        version = OrderOfEliteVersion.objects.create(
            author=user,
            based_on=GrandCouncilController.get_live_version(),
            version_number=next_number,
            status=OrderOfEliteVersion.DRAFT,
        )

        return GrandCouncilController._serialize_version(version, viewer=user)

    @staticmethod
    @transaction.atomic
    def add_condition(user, version_id, title, content, condition_type,
                      consequence, png_days, bounty_amount):
        version = GrandCouncilController._get_draft_for_author(user, version_id)
        title, content, condition_type, consequence, png_days, bounty_amount = \
            GrandCouncilController._clean_condition_fields(
                title, content, condition_type, consequence, png_days, bounty_amount)

        next_order = version.conditions.count()
        Condition.objects.create(
            version=version,
            order=next_order,
            title=title,
            content=content,
            condition_type=condition_type,
            consequence=consequence,
            png_days=png_days,
            bounty_amount=bounty_amount,
        )

        return GrandCouncilController._serialize_version(version, viewer=user)

    @staticmethod
    @transaction.atomic
    def update_condition(user, version_id, condition_id, title, content,
                         condition_type, consequence, png_days, bounty_amount):
        version = GrandCouncilController._get_draft_for_author(user, version_id)
        try:
            condition = version.conditions.get(id=condition_id)
        except Condition.DoesNotExist:
            raise OOEException('This condition no longer exists.')

        title, content, condition_type, consequence, png_days, bounty_amount = \
            GrandCouncilController._clean_condition_fields(
                title, content, condition_type, consequence, png_days, bounty_amount)

        condition.title = title
        condition.content = content
        condition.condition_type = condition_type
        condition.consequence = consequence
        condition.png_days = png_days
        condition.bounty_amount = bounty_amount
        condition.save(update_fields=[
            'title', 'content', 'condition_type', 'consequence', 'png_days', 'bounty_amount'])

        return GrandCouncilController._serialize_version(version, viewer=user)

    @staticmethod
    @transaction.atomic
    def remove_condition(user, version_id, condition_id):
        version = GrandCouncilController._get_draft_for_author(user, version_id)
        version.conditions.filter(id=condition_id).delete()

        return GrandCouncilController._serialize_version(version, viewer=user)

    @staticmethod
    @transaction.atomic
    def discard_draft(user, version_id):
        version = GrandCouncilController._get_draft_for_author(user, version_id)
        version.status = OrderOfEliteVersion.DISCARDED
        version.resolved_at = timezone.now()
        version.save(update_fields=['status', 'resolved_at'])

        return {'status': 'success', 'message': 'The draft has been discarded.'}

    # ── Submission / peer approval ───────────────────────────

    @staticmethod
    @transaction.atomic
    def submit_for_approval(user, version_id):
        version = GrandCouncilController._get_draft_for_author(user, version_id)
        if not version.conditions.exists():
            raise OOEException('Add at least one condition before submitting.')

        now = timezone.now()
        threshold = GrandCouncilController._peer_threshold(user)

        if threshold == 0:
            version.status = OrderOfEliteVersion.OWNER_REVIEW
        else:
            version.status = OrderOfEliteVersion.PEER_REVIEW
        version.submitted_at = now
        version.save(update_fields=['status', 'submitted_at'])

        return {'status': 'success', 'message': 'The draft has been submitted for review.'}

    @staticmethod
    @transaction.atomic
    def cast_vote(user, version_id, decision):
        if decision not in (OrderOfEliteApproval.APPROVE, OrderOfEliteApproval.REJECT):
            raise OOEException('Invalid decision.')

        GrandCouncilController._require_current_member(user)

        try:
            version = OrderOfEliteVersion.objects.select_for_update().get(
                id=version_id, status=OrderOfEliteVersion.PEER_REVIEW)
        except OrderOfEliteVersion.DoesNotExist:
            raise OOEException('This version is not currently awaiting peer review.')

        if version.author_id == user.id:
            raise OOEException('You cannot vote on your own draft.')

        if OrderOfEliteApproval.objects.filter(version=version, member=user).exists():
            raise OOEException('You have already voted on this draft.')

        OrderOfEliteApproval.objects.create(version=version, member=user, decision=decision)

        threshold = GrandCouncilController._peer_threshold(version.author)
        approvals = OrderOfEliteApproval.objects.filter(version=version)
        approve_count = approvals.filter(decision=OrderOfEliteApproval.APPROVE).count()
        reject_count = approvals.filter(decision=OrderOfEliteApproval.REJECT).count()

        if approve_count >= threshold:
            version.status = OrderOfEliteVersion.OWNER_REVIEW
            version.save(update_fields=['status'])
        elif reject_count >= threshold:
            version.status = OrderOfEliteVersion.REJECTED
            version.resolved_at = timezone.now()
            version.save(update_fields=['status', 'resolved_at'])

        return GrandCouncilController._serialize_version(version, viewer=user)

    # ── Owner review (invoked from admin.py) ─────────────────

    @staticmethod
    @transaction.atomic
    def owner_publish(version):
        version = OrderOfEliteVersion.objects.select_for_update().get(id=version.id)
        if version.status != OrderOfEliteVersion.OWNER_REVIEW:
            raise OOEException('This version is not awaiting owner review.')

        now = timezone.now()

        OrderOfEliteVersion.objects.filter(status=OrderOfEliteVersion.PUBLISHED).update(
            status=OrderOfEliteVersion.SUPERSEDED, resolved_at=now)

        version.status = OrderOfEliteVersion.PUBLISHED
        version.owner_reviewed_at = now
        version.published_at = now
        version.save(update_fields=['status', 'owner_reviewed_at', 'published_at'])

    @staticmethod
    @transaction.atomic
    def owner_reject(version):
        version = OrderOfEliteVersion.objects.select_for_update().get(id=version.id)
        if version.status != OrderOfEliteVersion.OWNER_REVIEW:
            raise OOEException('This version is not awaiting owner review.')

        now = timezone.now()
        version.status = OrderOfEliteVersion.REJECTED
        version.owner_reviewed_at = now
        version.resolved_at = now
        version.save(update_fields=['status', 'owner_reviewed_at', 'resolved_at'])
