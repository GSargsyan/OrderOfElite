import time
import random

from django.core.cache import cache
from django.db.models import F

from ooe.users.models import User
from ooe.base.exceptions import OOEException
from ooe.base.events import emit_event, EventTypes
from ooe.items.constants import \
    HOUSES, \
    HOUSE_SELL_PERCENT, \
    CARS, \
    CAR_SELL_PERCENT, \
    GUNS, \
    GUN_SELL_PERCENT, \
    AIRPLANES, \
    AIRPLANE_SELL_PERCENT

from ooe.items.models import CarTransaction, GunTransaction, UserCar, UserGun, UserHouse


class ItemsController:
    def __init__(self):
        pass

    # ──────────────────────────────────────────────────────────
    # Stat Multipliers (plugs into User.get_stat_multipliers)
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def get_equipped_stat_multipliers(user):
        """
        Returns per-stat multipliers from currently equipped items.
        Called by User.get_stat_multipliers() to plug into the pipeline.
        """
        multipliers = {'attack': 1.0, 'defense': 1.0, 'driving': 1.0}

        # Equipped house (city-specific)
        equipped_house_qs = user.houses.filter(city=user.city, is_equipped=True).first()
        if equipped_house_qs:
            house_data = HOUSES.get(equipped_house_qs.house, {})
            multipliers['defense'] *= house_data.get('defense_multiplier', 1.0)

        # Equipped car (city-specific)
        equipped_car_qs = user.cars.filter(city=user.city, is_equipped=True).first()
        if equipped_car_qs:
            car_data = CARS.get(equipped_car_qs.car, {})
            multipliers['attack'] *= car_data.get('attack_multiplier', 1.0)
            multipliers['defense'] *= car_data.get('defense_multiplier', 1.0)
            multipliers['driving'] *= car_data.get('driving_multiplier', 1.0)

        # Equipped gun (player-bound, not city-specific)
        equipped_gun_qs = user.guns.filter(is_equipped=True).first()
        if equipped_gun_qs:
            gun_data = GUNS.get(equipped_gun_qs.gun, {})
            multipliers['attack'] *= gun_data.get('attack_multiplier', 1.0)

        return multipliers

    @staticmethod
    def get_equipped_multipliers_breakdown(user):
        """
        Returns a per-source breakdown of multipliers for the frontend tooltip.
        Format: { 'house': {'defense': 2.0}, 'car': {'attack': 1.5, ...}, 'gun': {'attack': 2.0} }
        """
        breakdown = {}

        equipped_house_qs = user.houses.filter(city=user.city, is_equipped=True).first()
        if equipped_house_qs:
            house_data = HOUSES.get(equipped_house_qs.house, {})
            dm = house_data.get('defense_multiplier', 1.0)
            if dm != 1.0:
                breakdown['house'] = {'defense': dm, 'name': house_data.get('name', '')}

        equipped_car_qs = user.cars.filter(city=user.city, is_equipped=True).first()
        if equipped_car_qs:
            car_data = CARS.get(equipped_car_qs.car, {})
            car_entry = {'name': car_data.get('name', '')}
            for stat in ('attack_multiplier', 'defense_multiplier', 'driving_multiplier'):
                v = car_data.get(stat, 1.0)
                if v != 1.0:
                    car_entry[stat.replace('_multiplier', '')] = v
            if len(car_entry) > 1:
                breakdown['car'] = car_entry

        equipped_gun_qs = user.guns.filter(is_equipped=True).first()
        if equipped_gun_qs:
            gun_data = GUNS.get(equipped_gun_qs.gun, {})
            am = gun_data.get('attack_multiplier', 1.0)
            if am != 1.0:
                breakdown['gun'] = {'attack': am, 'name': gun_data.get('name', '')}

        return breakdown

    # ──────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def _get_garage_capacity(user):
        """Returns the garage capacity of the user's equipped house, or 0 if none."""
        equipped_house = user.houses.filter(city=user.city, is_equipped=True).first()
        if not equipped_house:
            return 0
        return HOUSES.get(equipped_house.house, {}).get('garage_capacity', 0)

    @staticmethod
    def _count_cars_in_city(user):
        """Returns how many cars the user owns in the current city."""
        return user.cars.filter(city=user.city).count()

    @staticmethod
    def _auto_equip_best_car(user):
        """
        Auto-equips the most expensive car the user owns in their current city.
        Clears any existing equipped car first.
        Returns True if a car was equipped, False if no cars remain.
        """
        UserCar.objects.filter(user=user, city=user.city, is_equipped=True).update(is_equipped=False)

        # Pick the most expensive car the user owns
        best_car = None
        best_price = -1
        for uc in user.cars.filter(city=user.city):
            price = CARS.get(uc.car, {}).get('price', 0)
            if price > best_price:
                best_price = price
                best_car = uc

        if best_car:
            best_car.is_equipped = True
            best_car.save(update_fields=['is_equipped'])
            return True
        return False

    @staticmethod
    def _auto_equip_best_gun(user):
        """
        Auto-equips the most expensive gun the user owns.
        Clears any existing equipped gun first.
        Returns True if a gun was equipped, False if no guns remain.
        """
        UserGun.objects.filter(user=user, is_equipped=True).update(is_equipped=False)

        best_gun = None
        best_price = -1
        for ug in user.guns.all():
            price = GUNS.get(ug.gun, {}).get('price', 0)
            if price > best_price:
                best_price = price
                best_gun = ug

        if best_gun:
            best_gun.is_equipped = True
            best_gun.save(update_fields=['is_equipped'])
            return True
        return False

    # ──────────────────────────────────────────────────────────
    # Houses
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def get_user_houses(user: object):
        user_houses = user.houses.all()
        owns_in_cities = {house: [] for house in HOUSES}
        equipped_house_key = None

        for house in user_houses:
            owns_in_cities[house.house].append(house.city.name)
            if house.is_equipped and house.city_id == user.city_id:
                equipped_house_key = house.house

        return {
            key: {
                'name': house['name'],
                'price': house['price'],
                'defense_multiplier': house['defense_multiplier'],
                'garage_capacity': house['garage_capacity'],
                'maintenance_cost': house['maintenance_cost'],
                'owns_in_cities': owns_in_cities[key],
                'owns_in_current_city': user.city.name in owns_in_cities[key],
                'is_equipped': equipped_house_key == key,
            }
            for key, house in HOUSES.items()
        }

    @staticmethod
    def buy_house(user: object, house_name: str):
        if house_name not in HOUSES:
            raise OOEException('Invalid house name')

        if user.money_cash < HOUSES[house_name]['price']:
            raise OOEException('Not enough money')

        if user.houses.filter(city=user.city, house=house_name).exists():
            raise OOEException('Already owns this house in the current city')

        user.money_cash = F('money_cash') - HOUSES[house_name]['price']
        user.save()

        user.houses.create(
            house=house_name,
            city=user.city,
        )

        emit_event(EventTypes.ITEM_BOUGHT, actor=user, city=user.city, metadata={
            'item_type': 'house',
            'item_key': house_name,
            'price': HOUSES[house_name]['price'],
        })

        return {
            'status': 'success',
            'message': 'House bought',
        }

    @staticmethod
    def sell_house(user: object, house_name: str):
        if house_name not in HOUSES:
            raise OOEException('Invalid house name')

        house_record = user.houses.filter(house=house_name, city=user.city).first()
        if not house_record:
            raise OOEException('Does not own this house in the current city')

        if house_record.is_equipped:
            # Unequip all cars too since house is going away
            UserCar.objects.filter(user=user, city=user.city, is_equipped=True).update(is_equipped=False)

        user.money_cash = F('money_cash') + int(HOUSES[house_name]['price'] * HOUSE_SELL_PERCENT)
        user.save()

        house_record.delete()

        emit_event(EventTypes.ITEM_SOLD, actor=user, city=user.city, metadata={
            'item_type': 'house',
            'item_key': house_name,
            'price': int(HOUSES[house_name]['price'] * HOUSE_SELL_PERCENT),
        })

        return {
            'status': 'success',
            'message': 'House sold',
        }

    @staticmethod
    def equip_house(user: object, house_name: str):
        if house_name not in HOUSES:
            raise OOEException('Invalid house name')

        house_record = user.houses.filter(house=house_name, city=user.city).first()
        if not house_record:
            raise OOEException('Does not own this house in the current city')

        new_capacity = HOUSES[house_name]['garage_capacity']
        current_car_count = ItemsController._count_cars_in_city(user)

        if current_car_count > new_capacity:
            raise OOEException(
                f'This house has a garage capacity of {new_capacity}, '
                f'but you own {current_car_count} car(s). '
                f'Please sell {current_car_count - new_capacity} car(s) first.'
            )

        # Unequip any currently equipped house in this city
        user.houses.filter(city=user.city, is_equipped=True).update(is_equipped=False)

        house_record.is_equipped = True
        house_record.save(update_fields=['is_equipped'])

        return {
            'status': 'success',
            'message': 'House equipped',
        }

    @staticmethod
    def unequip_house(user: object):
        updated = user.houses.filter(city=user.city, is_equipped=True).update(is_equipped=False)
        if not updated:
            raise OOEException('No house is currently equipped in this city')

        # Unequip cars too — no house, no garage
        UserCar.objects.filter(user=user, city=user.city, is_equipped=True).update(is_equipped=False)

        return {
            'status': 'success',
            'message': 'House unequipped',
        }

    # ──────────────────────────────────────────────────────────
    # Cars
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def get_user_cars(user: object):
        user_cars = user.cars.filter(city=user.city)
        counts = {}
        equipped_car_key = None
        for uc in user_cars:
            counts[uc.car] = counts.get(uc.car, 0) + 1
            if uc.is_equipped:
                equipped_car_key = uc.car

        garage_capacity = ItemsController._get_garage_capacity(user)
        current_car_count = ItemsController._count_cars_in_city(user)

        return {
            key: {
                'name': car['name'],
                'price': car['price'],
                'driving_multiplier': car['driving_multiplier'],
                'defense_multiplier': car['defense_multiplier'],
                'attack_multiplier': car['attack_multiplier'],
                'count_in_current_city': counts.get(key, 0),
                'is_equipped': equipped_car_key == key,
            }
            for key, car in CARS.items()
        } | {
            '__garage': {
                'capacity': garage_capacity,
                'used': current_car_count,
            }
        }

    @staticmethod
    def buy_car(user: object, car_name: str):
        if car_name not in CARS:
            raise OOEException('Invalid car name')

        if user.money_cash < CARS[car_name]['price']:
            raise OOEException('Not enough money')

        # Check garage capacity
        garage_capacity = ItemsController._get_garage_capacity(user)
        current_count = ItemsController._count_cars_in_city(user)
        if current_count >= garage_capacity:
            if garage_capacity == 0:
                raise OOEException('You need an equipped house with a garage to own a car.')
            raise OOEException(
                f'Garage is full ({current_count}/{garage_capacity}). '
                f'Sell a car or upgrade your house.'
            )

        user.money_cash = F('money_cash') - CARS[car_name]['price']
        user.save()

        user.cars.create(
            car=car_name,
            city=user.city,
        )

        CarTransaction.objects.create(
            user=user,
            car=car_name,
            city=user.city,
            action=CarTransaction.BUY,
            price=CARS[car_name]['price'],
        )

        emit_event(EventTypes.ITEM_BOUGHT, actor=user, city=user.city, metadata={
            'item_type': 'car',
            'item_key': car_name,
            'price': CARS[car_name]['price'],
        })

        return {
            'status': 'success',
            'message': 'Car bought',
        }

    @staticmethod
    def sell_car(user: object, car_name: str):
        if car_name not in CARS:
            raise OOEException('Invalid car name')

        car_to_sell = user.cars.filter(car=car_name, city=user.city).order_by('id').first()
        if not car_to_sell:
            raise OOEException('Does not own this car in the current city')

        was_equipped = car_to_sell.is_equipped

        sell_price = int(CARS[car_name]['price'] * CAR_SELL_PERCENT)
        user.money_cash = F('money_cash') + sell_price
        user.save()

        car_to_sell.delete()

        CarTransaction.objects.create(
            user=user,
            car=car_name,
            city=user.city,
            action=CarTransaction.SELL,
            price=sell_price,
        )

        # If the sold car was equipped, auto-equip next best
        if was_equipped:
            ItemsController._auto_equip_best_car(user)

        emit_event(EventTypes.ITEM_SOLD, actor=user, city=user.city, metadata={
            'item_type': 'car',
            'item_key': car_name,
            'price': sell_price,
        })

        return {
            'status': 'success',
            'message': 'Car sold',
        }

    @staticmethod
    def equip_car(user: object, car_name: str):
        if car_name not in CARS:
            raise OOEException('Invalid car name')

        car_record = user.cars.filter(car=car_name, city=user.city).first()
        if not car_record:
            raise OOEException('Does not own this car in the current city')

        # Unequip current car
        user.cars.filter(city=user.city, is_equipped=True).update(is_equipped=False)

        car_record.is_equipped = True
        car_record.save(update_fields=['is_equipped'])

        return {
            'status': 'success',
            'message': 'Car equipped',
        }

    @staticmethod
    def unequip_car(user: object):
        updated = user.cars.filter(city=user.city, is_equipped=True).update(is_equipped=False)
        if not updated:
            raise OOEException('No car is currently equipped in this city')

        return {
            'status': 'success',
            'message': 'Car unequipped',
        }

    # ──────────────────────────────────────────────────────────
    # Guns (player-bound, not city-specific)
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def get_user_guns(user: object):
        user_guns = user.guns.all()
        counts = {}
        equipped_gun_key = None
        for ug in user_guns:
            counts[ug.gun] = counts.get(ug.gun, 0) + 1
            if ug.is_equipped:
                equipped_gun_key = ug.gun

        return {
            key: {
                'name': gun['name'],
                'price': gun['price'],
                'attack_multiplier': gun['attack_multiplier'],
                'count': counts.get(key, 0),
                'is_equipped': equipped_gun_key == key,
            }
            for key, gun in GUNS.items()
        }

    @staticmethod
    def buy_gun(user: object, gun_name: str):
        if gun_name not in GUNS:
            raise OOEException('Invalid gun name')

        if user.money_cash < GUNS[gun_name]['price']:
            raise OOEException('Not enough money')

        user.money_cash = F('money_cash') - GUNS[gun_name]['price']
        user.save()

        user.guns.create(
            gun=gun_name,
        )

        GunTransaction.objects.create(
            user=user,
            gun=gun_name,
            action=GunTransaction.BUY,
            price=GUNS[gun_name]['price'],
        )

        emit_event(EventTypes.ITEM_BOUGHT, actor=user, city=user.city, metadata={
            'item_type': 'gun',
            'item_key': gun_name,
            'price': GUNS[gun_name]['price'],
        })

        return {
            'status': 'success',
            'message': 'Gun bought',
        }

    @staticmethod
    def sell_gun(user: object, gun_name: str):
        if gun_name not in GUNS:
            raise OOEException('Invalid gun name')

        gun_to_sell = user.guns.filter(gun=gun_name).order_by('id').first()
        if not gun_to_sell:
            raise OOEException('Does not own this gun')

        was_equipped = gun_to_sell.is_equipped

        sell_price = int(GUNS[gun_name]['price'] * GUN_SELL_PERCENT)
        user.money_cash = F('money_cash') + sell_price
        user.save()

        gun_to_sell.delete()

        GunTransaction.objects.create(
            user=user,
            gun=gun_name,
            action=GunTransaction.SELL,
            price=sell_price,
        )

        # If the sold gun was equipped, auto-equip next best
        if was_equipped:
            ItemsController._auto_equip_best_gun(user)

        emit_event(EventTypes.ITEM_SOLD, actor=user, city=user.city, metadata={
            'item_type': 'gun',
            'item_key': gun_name,
            'price': sell_price,
        })

        return {
            'status': 'success',
            'message': 'Gun sold',
        }

    @staticmethod
    def equip_gun(user: object, gun_name: str):
        if gun_name not in GUNS:
            raise OOEException('Invalid gun name')

        gun_record = user.guns.filter(gun=gun_name).first()
        if not gun_record:
            raise OOEException('Does not own this gun')

        # Unequip current gun
        user.guns.filter(is_equipped=True).update(is_equipped=False)

        gun_record.is_equipped = True
        gun_record.save(update_fields=['is_equipped'])

        return {
            'status': 'success',
            'message': 'Gun equipped',
        }

    @staticmethod
    def unequip_gun(user: object):
        updated = user.guns.filter(is_equipped=True).update(is_equipped=False)
        if not updated:
            raise OOEException('No gun is currently equipped')

        return {
            'status': 'success',
            'message': 'Gun unequipped',
        }

    # ──────────────────────────────────────────────────────────
    # Airplanes (unchanged)
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def get_user_airplanes(user: object):
        user_airplanes = user.airplanes.all()
        owned_airplanes = {ap.airplane for ap in user_airplanes}

        return {
            key: {
                'name': airplane['name'],
                'price': airplane['price'],
                'speed_multiplier': airplane['speed_multiplier'],
                'price_multiplier': airplane['price_multiplier'],
                'cooldown': airplane['cooldown'],
                'cooldown_minutes': airplane['cooldown_minutes'],
                'owned': key in owned_airplanes or key == 'commercial_flight',
            }
            for key, airplane in AIRPLANES.items()
        }

    @staticmethod
    def buy_airplane(user: object, airplane_name: str):
        if airplane_name not in AIRPLANES:
            raise OOEException('Invalid airplane name')

        if airplane_name == 'commercial_flight':
            raise OOEException('Cannot buy commercial flight')

        if user.money_cash < AIRPLANES[airplane_name]['price']:
            raise OOEException('Not enough money')

        if user.airplanes.filter(airplane=airplane_name).exists():
            raise OOEException('Already owns this airplane')

        user.money_cash = F('money_cash') - AIRPLANES[airplane_name]['price']
        user.save()

        user.airplanes.create(
            airplane=airplane_name,
        )

        emit_event(EventTypes.ITEM_BOUGHT, actor=user, city=user.city, metadata={
            'item_type': 'airplane',
            'item_key': airplane_name,
            'price': AIRPLANES[airplane_name]['price'],
        })

        return {
            'status': 'success',
            'message': 'Airplane bought',
        }

    @staticmethod
    def sell_airplane(user: object, airplane_name: str):
        if airplane_name not in AIRPLANES:
            raise OOEException('Invalid airplane name')

        if airplane_name == 'commercial_flight':
            raise OOEException('Cannot sell commercial flight')

        if not user.airplanes.filter(airplane=airplane_name).exists():
            raise OOEException('Does not own this airplane')

        user.money_cash = F('money_cash') + int(AIRPLANES[airplane_name]['price'] * AIRPLANE_SELL_PERCENT)
        user.save()

        user.airplanes.filter(airplane=airplane_name).delete()

        emit_event(EventTypes.ITEM_SOLD, actor=user, city=user.city, metadata={
            'item_type': 'airplane',
            'item_key': airplane_name,
            'price': int(AIRPLANES[airplane_name]['price'] * AIRPLANE_SELL_PERCENT),
        })

        return {
            'status': 'success',
            'message': 'Airplane sold',
        }