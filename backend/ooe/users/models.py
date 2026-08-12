from django.db import models
from django.db.models import F
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager

from ooe.chat.models import ChatRoom
from ooe.base.constants import RANK_EXPS


class UserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError("The Username field must be set")

        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        return user


class User(AbstractBaseUser):
    username = models.CharField(max_length=30, unique=True)
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_time = models.DateTimeField(null=True, blank=True)
    money_cash = models.IntegerField(default=0)
    money_bank = models.IntegerField(default=0)
    city = models.ForeignKey('cities.City', on_delete=models.CASCADE, default=1)
    exp = models.IntegerField(default=0)
    rank = models.IntegerField(default=1)
    attack_points = models.IntegerField(default=0)
    defense_points = models.IntegerField(default=0)
    driving_points = models.IntegerField(default=0)
    health = models.IntegerField(default=100)
    elite_coins = models.IntegerField(default=10)
    kills = models.IntegerField(default=0)
    is_premium = models.BooleanField(default=False)
    premium_since = models.DateTimeField(null=True, blank=True)
    # Persona non grata: active while png_until is in the future
    png_until = models.DateTimeField(null=True, blank=True)
    # Permanent dossier mark: has broken a Seal at least once
    seal_breaker = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = 'ooe_users'

    def get_stat_multipliers(self):
        """
        Combines per-stat multipliers from every modifier source
        multiplicatively. New sources (houses, cars, guns, ...) plug in
        by appending to the sources list.
        """
        from ooe.citadel.controllers import CitadelController
        from ooe.items.controllers import ItemsController

        sources = [
            CitadelController.get_stat_multipliers(self),
            ItemsController.get_equipped_stat_multipliers(self),
        ]

        multipliers = {'attack': 1.0, 'defense': 1.0, 'driving': 1.0}
        for source in sources:
            for stat, value in source.items():
                multipliers[stat] *= value

        return multipliers

    def get_effective_stats(self):
        """Base skill points with all active multipliers applied."""
        multipliers = self.get_stat_multipliers()

        return {
            'attack': int(self.attack_points * multipliers['attack']),
            'defense': int(self.defense_points * multipliers['defense']),
            'driving': int(self.driving_points * multipliers['driving']),
        }

    def is_persona_non_grata(self):
        from django.utils import timezone
        return self.png_until is not None and self.png_until > timezone.now()

    def get_rank_progress(self):
        if self.rank + 1 not in RANK_EXPS:
            return 100.0

        next_rank_exp = RANK_EXPS[self.rank + 1]
        curr_rank_exp = RANK_EXPS[self.rank]

        abs_diff = next_rank_exp - curr_rank_exp
        exp_passed = self.exp - curr_rank_exp

        progress = (exp_passed / abs_diff) * 100

        return progress

    def get_preview_data(self):
        from ooe.travel.controllers import TravelController
        from ooe.citadel.controllers import CitadelController
        from ooe.items.controllers import ItemsController
        TravelController.check_and_complete_active_flight(self)

        active_stay = CitadelController.get_active_stay(self)
        effective_stats = self.get_effective_stats()
        multipliers = self.get_stat_multipliers()
        is_png = self.is_persona_non_grata()

        # Per-source multiplier breakdown for the tooltip
        item_breakdown = ItemsController.get_equipped_multipliers_breakdown(self)
        citadel_multipliers = CitadelController.get_stat_multipliers(self)
        skill_multipliers = {
            'citadel': citadel_multipliers,
            **item_breakdown,
        }

        res = {
            'username': self.username,
            'city': self.city.name,
            'is_premium': self.is_premium,
            'persona_non_grata': is_png,
            'png_until': self.png_until.timestamp() if is_png else 0,
            'seal_breaker': self.seal_breaker,
            'money_cash': self.money_cash,
            'health': self.health,
            'elite_coins': self.elite_coins,
            'rank': self.rank,
            'rank_progress': self.get_rank_progress(),
            # Effective (multiplied) stats
            'attack_points': effective_stats['attack'],
            'defense_points': effective_stats['defense'],
            'driving_points': effective_stats['driving'],
            # Raw base stats (no multipliers)
            'base_attack_points': self.attack_points,
            'base_defense_points': self.defense_points,
            'base_driving_points': self.driving_points,
            # Combined multipliers per skill
            'attack_multiplier': round(multipliers['attack'], 4),
            'defense_multiplier': round(multipliers['defense'], 4),
            'driving_multiplier': round(multipliers['driving'], 4),
            # Per-source breakdown for tooltip
            'skill_multipliers': skill_multipliers,
            'in_flight': False,
            'flight_data': None,
            'in_citadel': active_stay is not None,
            'citadel_data': {
                'entered_at': active_stay.entered_at.timestamp(),
                'stay_until': active_stay.scheduled_until.timestamp(),
            } if active_stay else None,
        }

        # Include active flight data if the user is currently in flight
        active_flight = self.flights.filter(arrived_at__isnull=True).select_related(
            'origin_city', 'destination_city'
        ).first()
        if active_flight:
            res['in_flight'] = True
            res['flight_data'] = {
                'origin_city': active_flight.origin_city.name,
                'destination_city': active_flight.destination_city.name,
                'arrival_time': active_flight.arrival_time.timestamp(),
                'departed_at': active_flight.departed_at.timestamp(),
            }

        return res

    def add_default_chat_rooms(self):
        chat_room = ChatRoom.objects.filter(city=self.city, chat_type='city').first()
        if chat_room:
            chat_room.users.add(self)

    def add_exp(self, exp: int):
        User.objects.filter(id=self.id).update(exp=F('exp') + exp)

        self.refresh_from_db()

        # Update rank if needed
        if self.rank + 1 in RANK_EXPS and self.exp >= RANK_EXPS[self.rank + 1]:
            self.rank += 1
            self.save(update_fields=['rank'])

    def get_profile_data(self, requesting_user=None):
        reviews = self.received_reviews.select_related('reviewer').order_by('created_at')
        total_rating = sum(r.rating for r in reviews)
        count = len(reviews)
        overall_rating = round(total_rating / count, 1) if count > 0 else None
        
        serialized_reviews = [{
            'id': r.id,
            'reviewer': r.reviewer.username,
            'rating': r.rating,
            'text': r.text,
            'created_at': r.created_at.isoformat()
        } for r in reviews]
        
        cooldown_seconds = 0
        if requesting_user and requesting_user != self:
            from datetime import timedelta
            from django.utils import timezone
            one_day_ago = timezone.now() - timedelta(hours=24)
            last_review = self.received_reviews.filter(reviewer=requesting_user, created_at__gt=one_day_ago).order_by('-created_at').first()
            if last_review:
                elapsed = timezone.now() - last_review.created_at
                cooldown_seconds = max(0, int(86400 - elapsed.total_seconds()))

        res = {
            'username': self.username,
            'rank': self.rank,
            'overall_rating': overall_rating,
            'reviews_count': count,
            'reviews': serialized_reviews,
            'cooldown_seconds': cooldown_seconds,
            'persona_non_grata': self.is_persona_non_grata(),
            'seal_breaker': self.seal_breaker,
        }

        return res


class UserReview(models.Model):
    reviewer = models.ForeignKey('users.User', related_name='written_reviews', on_delete=models.CASCADE)
    reviewed = models.ForeignKey('users.User', related_name='received_reviews', on_delete=models.CASCADE)
    rating = models.IntegerField()
    text = models.CharField(max_length=250)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ooe_user_reviews'
        ordering = ['created_at']