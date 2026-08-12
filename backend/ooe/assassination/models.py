from django.db import models


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
