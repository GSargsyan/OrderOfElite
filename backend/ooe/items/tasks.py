from celery import shared_task


@shared_task
def charge_house_maintenance():
    """
    Celery beat task — runs every 60 seconds.

    Charges each user with an equipped house a per-minute maintenance fee:
        charge = floor(maintenance_cost / 1440)   (daily cost ÷ 1440 minutes)

    If the user cannot afford the charge, the house is force-unequipped
    (and any equipped car in that city is also unequipped).
    No notification is sent — the player must re-equip manually.
    """
    from django.db.models import F
    from ooe.items.models import UserHouse, UserCar
    from ooe.items.constants import HOUSES

    equipped_houses = UserHouse.objects.filter(
        is_equipped=True
    ).select_related('user', 'city')

    for house_record in equipped_houses:
        user = house_record.user
        house_data = HOUSES.get(house_record.house)
        if not house_data:
            continue

        daily_cost = house_data['maintenance_cost']
        per_minute_charge = daily_cost // 1440  # integer floor

        if per_minute_charge == 0:
            continue

        if user.money_cash >= per_minute_charge:
            # Deduct atomically
            from ooe.users.models import User
            User.objects.filter(id=user.id).update(
                money_cash=F('money_cash') - per_minute_charge
            )
        else:
            # Force-evict: unequip house and any parked car
            house_record.is_equipped = False
            house_record.save(update_fields=['is_equipped'])
            UserCar.objects.filter(
                user=user,
                city=house_record.city,
                is_equipped=True,
            ).update(is_equipped=False)
