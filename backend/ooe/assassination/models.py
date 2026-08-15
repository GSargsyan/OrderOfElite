from django.db import models

from ooe.assassination.combat import ATTACK_TYPE_CHOICES


class SearchRecord(models.Model):
    """
    A single intel search, paid for in Elite Coins. The result snapshot is
    captured immediately at click time (search_type/city/status all reflect
    the target's state when the search was made, not when it resolves) but
    withheld from API responses until ready_at has passed — same lazy-reveal
    idiom as FlightLog/CitadelStay elsewhere in this codebase, no Celery task
    needed for the delay itself.
    """
    CITY = 'city'
    GLOBAL = 'global'
    TYPE_CHOICES = [(CITY, 'City'), (GLOBAL, 'Global')]

    STATUS_CITADEL = 'citadel'
    STATUS_FLIGHT = 'flight'
    STATUS_REGULAR = 'regular'
    STATUS_CHOICES = [
        (STATUS_CITADEL, 'Citadel'),
        (STATUS_FLIGHT, 'Flight'),
        (STATUS_REGULAR, 'Regular'),
    ]

    searcher = models.ForeignKey('users.User', related_name='searches_made', on_delete=models.CASCADE)
    target = models.ForeignKey('users.User', related_name='searches_received', on_delete=models.CASCADE)
    search_type = models.CharField(max_length=6, choices=TYPE_CHOICES)
    cost = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    ready_at = models.DateTimeField()

    # Snapshot captured at click time
    searcher_city_name = models.CharField(max_length=30)
    found = models.BooleanField()
    result_city_name = models.CharField(max_length=30, null=True, blank=True)
    result_status = models.CharField(max_length=8, choices=STATUS_CHOICES, null=True, blank=True)

    class Meta:
        db_table = 'ooe_search_records'
        ordering = ['-created_at']


class Kill(models.Model):
    """
    One resolved attack attempt (whatever the outcome). The permanent
    combat record — this is the table Seals' future PLAYER_KILLED trigger
    and KILL/REFRAIN_FROM_ATTACKING obligation predicates will read.

    Kept even after a party's other data is wiped on death: it's history,
    not live state, and both Seals adjudication and any future Graveyard/
    stats feature need it to survive the death it records.
    """
    KILL = 'kill'
    BACKFIRE = 'backfire'
    MUTUAL = 'mutual'
    SURVIVE = 'survive'
    OUTCOME_CHOICES = [
        (KILL, 'Kill'),
        (BACKFIRE, 'Backfire'),
        (MUTUAL, 'Mutual elimination'),
        (SURVIVE, 'Survive'),
    ]

    attacker = models.ForeignKey('users.User', related_name='attacks_made', on_delete=models.CASCADE)
    defender = models.ForeignKey('users.User', related_name='attacks_received', on_delete=models.CASCADE)
    attack_type = models.CharField(max_length=10, choices=ATTACK_TYPE_CHOICES)
    budget = models.IntegerField()
    city = models.ForeignKey('cities.City', related_name='kills', on_delete=models.CASCADE)

    # Snapshots — items get wiped from a dead player's inventory, so the
    # gear actually used in the exchange only survives here.
    attacker_gun = models.CharField(max_length=50, blank=True, default='')
    attacker_car = models.CharField(max_length=50, blank=True, default='')
    defender_gun = models.CharField(max_length=50, blank=True, default='')
    defender_car = models.CharField(max_length=50, blank=True, default='')

    attacker_health_before = models.IntegerField()
    attacker_health_after = models.IntegerField()
    defender_health_before = models.IntegerField()
    defender_health_after = models.IntegerField()

    outcome = models.CharField(max_length=10, choices=OUTCOME_CHOICES)
    money_looted = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ooe_kills'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['attacker', 'created_at']),
            models.Index(fields=['defender', 'created_at']),
        ]
