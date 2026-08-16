from django.db import models


class CouncilTerm(models.Model):
    """
    One weekly rotation's roster. A full reshuffle happens every Monday
    00:00 UTC (see engine.run_weekly_rotation) - the current term is the
    one row with ended_at IS NULL.
    """
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ooe_grand_council_terms'
        ordering = ['-started_at']


class CouncilMembership(models.Model):
    """
    One seat in one term. Snapshots the selection criteria at rotation
    time so historical rosters stay meaningful even as the user's live
    stats change afterward.
    """
    term = models.ForeignKey(CouncilTerm, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='council_memberships')
    seat = models.IntegerField()
    rank_snapshot = models.IntegerField()
    kills_snapshot = models.IntegerField()
    net_worth_snapshot = models.BigIntegerField()

    class Meta:
        db_table = 'ooe_grand_council_memberships'
        unique_together = [('term', 'user')]
        ordering = ['seat']
        indexes = [
            models.Index(fields=['term', 'seat']),
        ]


class OrderOfEliteVersion(models.Model):
    """
    One authored version of the Order of Elite ruleset. Lifecycle:
    draft -> peer_review -> owner_review -> published, with rejected/
    discarded/superseded as terminal off-ramps. Only one version may be
    published at a time; older published versions become superseded.
    """
    DRAFT = 'draft'
    PEER_REVIEW = 'peer_review'
    OWNER_REVIEW = 'owner_review'
    PUBLISHED = 'published'
    SUPERSEDED = 'superseded'
    REJECTED = 'rejected'
    DISCARDED = 'discarded'

    STATUS_CHOICES = [
        (DRAFT, 'Draft'),
        (PEER_REVIEW, 'Peer review'),
        (OWNER_REVIEW, 'Owner review'),
        (PUBLISHED, 'Published'),
        (SUPERSEDED, 'Superseded'),
        (REJECTED, 'Rejected'),
        (DISCARDED, 'Discarded'),
    ]

    # A version still being decided on. Only one may be open at a time
    # platform-wide (enforced in the controller).
    OPEN_STATUSES = [DRAFT, PEER_REVIEW, OWNER_REVIEW]

    author = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True,
        related_name='authored_oe_versions')
    based_on = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='revisions')
    version_number = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    owner_reviewed_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'ooe_grand_council_oe_versions'
        ordering = ['-version_number']


class Condition(models.Model):
    """
    One entry in an Order of Elite version: either purely informative
    text, or a Rule that carries an (unenforced, display-only for now)
    consequence.
    """
    INFORMATIVE = 'informative'
    RULE = 'rule'
    TYPE_CHOICES = [
        (INFORMATIVE, 'Informative'),
        (RULE, 'Rule'),
    ]

    NONE = 'none'
    PERSONA_NON_GRATA = 'persona_non_grata'
    BLACKLIST = 'blacklist'
    CONSEQUENCE_CHOICES = [
        (NONE, 'None'),
        (PERSONA_NON_GRATA, 'Persona non grata'),
        (BLACKLIST, 'Blacklist'),
    ]

    version = models.ForeignKey(OrderOfEliteVersion, on_delete=models.CASCADE, related_name='conditions')
    order = models.IntegerField(default=0)
    title = models.CharField(max_length=120)
    content = models.TextField()
    condition_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=INFORMATIVE)
    consequence = models.CharField(max_length=20, choices=CONSEQUENCE_CHOICES, default=NONE, blank=True)
    # Set iff consequence == PERSONA_NON_GRATA
    png_days = models.IntegerField(null=True, blank=True)
    # Set iff consequence == BLACKLIST
    bounty_amount = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = 'ooe_grand_council_conditions'
        ordering = ['order', 'id']


class OrderOfEliteApproval(models.Model):
    """
    One current council member's vote on a version awaiting peer review.
    One vote per member per version, immutable once cast.
    """
    APPROVE = 'approve'
    REJECT = 'reject'
    DECISION_CHOICES = [
        (APPROVE, 'Approve'),
        (REJECT, 'Reject'),
    ]

    version = models.ForeignKey(OrderOfEliteVersion, on_delete=models.CASCADE, related_name='approvals')
    member = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='oe_approvals')
    decision = models.CharField(max_length=10, choices=DECISION_CHOICES)
    decided_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ooe_grand_council_approvals'
        unique_together = [('version', 'member')]
