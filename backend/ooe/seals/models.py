from django.db import models


class Seal(models.Model):
    """
    A binding promise between two players.

    party_a is the creator, party_b the counterparty who signs.
    `compiled` holds the clause structures produced at authoring time;
    `rendered_text` is the deterministic formal rendering both parties
    see and sign. The raw text is kept only as flavor/history.
    """
    DRAFT = 'draft'
    PENDING_SIGNATURE = 'pending_signature'
    ACTIVE = 'active'
    FULFILLED = 'fulfilled'
    BREACHED = 'breached'
    DECLINED = 'declined'
    WITHDRAWN = 'withdrawn'
    ANNULLED = 'annulled'
    EXPIRED = 'expired'
    # A party died with this Seal still in play. Distinct from ANNULLED
    # (mutual consent) and EXPIRED (deadline) — permadeath makes the
    # underlying promise moot rather than resolved either way.
    OBSOLETED = 'obsoleted'

    STATUS_CHOICES = [
        (DRAFT, 'Draft'),
        (PENDING_SIGNATURE, 'Pending signature'),
        (ACTIVE, 'Active'),
        (FULFILLED, 'Fulfilled'),
        (BREACHED, 'Breached'),
        (DECLINED, 'Declined'),
        (WITHDRAWN, 'Withdrawn'),
        (ANNULLED, 'Annulled'),
        (EXPIRED, 'Expired'),
        (OBSOLETED, 'Obsoleted'),
    ]

    # A Seal is still "in play" while in one of these statuses.
    ACTIVE_STATUSES = [DRAFT, PENDING_SIGNATURE, ACTIVE]

    RESOLVED_STATUSES = [FULFILLED, BREACHED, DECLINED, WITHDRAWN, ANNULLED, EXPIRED, OBSOLETED]

    creator = models.ForeignKey(
        'users.User', on_delete=models.CASCADE, related_name='seals_created')
    counterparty = models.ForeignKey(
        'users.User', on_delete=models.CASCADE, related_name='seals_received')
    raw_text = models.CharField(max_length=400)
    compiled = models.JSONField(default=dict)
    rendered_text = models.TextField()
    penalty_png_days = models.IntegerField()
    deadline_days = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=DRAFT)
    annul_requested_by = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='seal_annul_requests')
    created_at = models.DateTimeField(auto_now_add=True)
    signed_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'ooe_seals'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['creator', 'status']),
            models.Index(fields=['counterparty', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]

    def party_ref_of(self, user):
        if user.id == self.creator_id:
            return 'party_a'
        if user.id == self.counterparty_id:
            return 'party_b'
        return None

    def user_of(self, party_ref):
        return self.creator if party_ref == 'party_a' else self.counterparty


class SealClause(models.Model):
    """
    One obligation owed by one party, gated by a trigger.

    Lifecycle: waiting_trigger -> armed -> fulfilled | breached,
    or lapsed if the trigger never fires within the trigger window.
    """
    WAITING_TRIGGER = 'waiting_trigger'
    ARMED = 'armed'
    FULFILLED = 'fulfilled'
    BREACHED = 'breached'
    LAPSED = 'lapsed'

    STATUS_CHOICES = [
        (WAITING_TRIGGER, 'Waiting trigger'),
        (ARMED, 'Armed'),
        (FULFILLED, 'Fulfilled'),
        (BREACHED, 'Breached'),
        (LAPSED, 'Lapsed'),
    ]

    seal = models.ForeignKey(Seal, on_delete=models.CASCADE, related_name='clauses')
    obligor = models.CharField(max_length=10)  # 'party_a' | 'party_b'
    trigger = models.JSONField()               # {'predicate': ..., 'args': {...}}
    obligation = models.JSONField()            # {'predicate': ..., 'args': {...}}
    deadline_days = models.IntegerField()
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=WAITING_TRIGGER)
    # For TIME_REACHED triggers: the exact moment the clause arms.
    trigger_at = models.DateTimeField(null=True, blank=True)
    armed_at = models.DateTimeField(null=True, blank=True)
    deadline_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'ooe_seal_clauses'
        indexes = [
            models.Index(fields=['status', 'deadline_at']),
            models.Index(fields=['status', 'trigger_at']),
        ]


class SealTriggerIndex(models.Model):
    """
    Indexed lookup from a GameEvent to the clauses it may affect, so an
    event is matched with one query instead of scanning all active seals.
    Rows exist only while the clause is waiting (kind='trigger') or
    armed (kind='obligation'), and are removed once the clause resolves.
    """
    TRIGGER = 'trigger'
    OBLIGATION = 'obligation'

    clause = models.ForeignKey(
        SealClause, on_delete=models.CASCADE, related_name='index_rows')
    kind = models.CharField(max_length=10)     # 'trigger' | 'obligation'
    event_type = models.CharField(max_length=40)
    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE, related_name='seal_index_rows')

    class Meta:
        db_table = 'ooe_seal_trigger_index'
        indexes = [
            models.Index(fields=['event_type', 'user']),
        ]


class SealCompileLog(models.Model):
    """
    Append-only record of every compilation attempt: the player's raw
    conditions, the raw LLM response, and the outcome. Failed rows show
    whether a rejected request was genuinely invalid or a use case worth
    adding to the predicate vocabulary.
    """
    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE, related_name='seal_compile_logs')
    counterparty_username = models.CharField(max_length=30)
    raw_text = models.CharField(max_length=400)
    success = models.BooleanField()
    reason_code = models.CharField(max_length=20, null=True, blank=True)
    response_raw = models.TextField(blank=True, default='')
    clauses = models.JSONField(null=True, blank=True)
    model = models.CharField(max_length=40)
    latency_ms = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ooe_seal_compile_log'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['success', 'created_at']),
        ]


class PersonaNonGrataLog(models.Model):
    """
    Append-only record of every persona non grata imposition, for
    auditability and future appeals (Grand Council). The live status
    itself is User.png_until.
    """
    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE, related_name='png_log')
    seal = models.ForeignKey(
        Seal, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='png_impositions')
    days = models.IntegerField()
    reason = models.CharField(max_length=250)
    imposed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ooe_persona_non_grata_log'
        ordering = ['-imposed_at']
