from django.db import models


class MissionLog(models.Model):
    mission = models.CharField(max_length=30)
    primary_user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='primary_user')
    reward = models.IntegerField(default=0)

    class Meta:
        db_table = 'ooe_mission_log'


class PartyMission(models.Model):
    """
    A multiplayer mission (Exfiltration, High-Profile Target Operation).
    Role structure (how many of what role) lives in
    ooe.missions.constants.PARTY_MISSIONS, not on the model — the
    lobby -> ready -> start -> resolve -> claim state machine below is
    identical for a 2-role and a 4-role mission, only PARTY_MISSIONS
    differs between them.
    """
    LOBBY = 'lobby'
    IN_PROGRESS = 'in_progress'
    RESOLVED = 'resolved'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (LOBBY, 'Lobby'),
        (IN_PROGRESS, 'In Progress'),
        (RESOLVED, 'Resolved'),
        (COMPLETED, 'Completed'),
        (FAILED, 'Failed'),
        (CANCELLED, 'Cancelled'),
    ]

    # statuses where the mission still blocks starting another mission of
    # the same type / still shows on the Missions tab as "yours" — includes
    # RESOLVED so an unclaimed reward keeps showing until it's claimed
    ACTIVE_STATUSES = [LOBBY, IN_PROGRESS, RESOLVED]

    # the narrower subset death/travel/Citadel-entry can still disrupt —
    # once RESOLVED the operation has already concluded, so losing a
    # participant at that point no longer unwinds anything
    DISRUPTIBLE_STATUSES = [LOBBY, IN_PROGRESS]

    EXFILTRATION = 'exfiltration'
    HVT = 'hvt'
    MISSION_TYPE_CHOICES = [
        (EXFILTRATION, 'Exfiltration'),
        (HVT, 'High-Profile Target Operation'),
    ]

    mission_type = models.CharField(max_length=15, choices=MISSION_TYPE_CHOICES)
    initiator = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='party_missions_initiated')
    city = models.ForeignKey('cities.City', on_delete=models.CASCADE, related_name='party_missions')
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=LOBBY)
    reward = models.IntegerField(default=0)
    exp_reward = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    resolves_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ooe_party_missions'
        indexes = [
            models.Index(fields=['initiator', 'status']),
            models.Index(fields=['status', 'resolves_at']),
        ]


class MissionParticipant(models.Model):
    INITIATOR = 'initiator'
    DRIVER = 'driver'
    ASSASSIN = 'assassin'
    ROLE_CHOICES = [
        (INITIATOR, 'Initiator'),
        (DRIVER, 'Driver'),
        (ASSASSIN, 'Assassin'),
    ]

    INVITED = 'invited'
    ACCEPTED = 'accepted'
    REJECTED = 'rejected'
    READY = 'ready'
    EXPIRED = 'expired'
    INVITE_STATUS_CHOICES = [
        (INVITED, 'Invited'),
        (ACCEPTED, 'Accepted'),
        (REJECTED, 'Rejected'),
        (READY, 'Ready'),
        (EXPIRED, 'Expired'),
    ]

    mission = models.ForeignKey(PartyMission, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='mission_participations')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    invite_status = models.CharField(max_length=10, choices=INVITE_STATUS_CHOICES, default=INVITED)
    # a car key for the Driver role, a gun key for the Assassin role; unused by Initiator
    equipped_item = models.CharField(max_length=50, null=True, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    invited_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'ooe_mission_participants'
        indexes = [
            models.Index(fields=['user', 'invite_status']),
            models.Index(fields=['mission', 'role']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['mission', 'user'], name='unique_participant_per_mission'),
        ]
