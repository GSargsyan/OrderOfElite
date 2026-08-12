class ProfileController:
    @staticmethod
    def get_profile_tab_data(user):
        """
        Aggregates the Profile tab payload by delegating to each domain's
        existing controller/serializer rather than re-deriving anything —
        this is a read-only summary view over state that's already computed
        elsewhere (User.get_preview_data, MissionsController, SkillsController,
        BlackMarketController).
        """
        from ooe.missions.controllers import MissionsController
        from ooe.users.controllers import SkillsController
        from ooe.users.constants import HOSPITAL_HEAL_COST_PER_POINT
        from ooe.black_market.controllers import BlackMarketController
        from ooe.items.constants import HOUSES, CARS, GUNS, AIRPLANES

        data = user.get_preview_data()

        # ── Items across all cities (unlike ItemsController.get_user_*, which
        # is scoped to the user's current city) ──────────────────────────
        items_by_city = {}
        for h in user.houses.select_related('city').all():
            bucket = items_by_city.setdefault(h.city.name, {'houses': [], 'cars': []})
            bucket['houses'].append({
                'key': h.house,
                'name': HOUSES.get(h.house, {}).get('name', h.house),
                'is_equipped': h.is_equipped,
            })
        for c in user.cars.select_related('city').all():
            bucket = items_by_city.setdefault(c.city.name, {'houses': [], 'cars': []})
            bucket['cars'].append({
                'key': c.car,
                'name': CARS.get(c.car, {}).get('name', c.car),
                'is_equipped': c.is_equipped,
            })

        # Guns and airplanes are player-bound, not city-scoped
        guns = [{
            'key': g.gun,
            'name': GUNS.get(g.gun, {}).get('name', g.gun),
            'is_equipped': g.is_equipped,
        } for g in user.guns.all()]

        airplanes = [{
            'key': a.airplane,
            'name': AIRPLANES.get(a.airplane, {}).get('name', a.airplane),
        } for a in user.airplanes.all()]

        # ── Black Market: condensed production summary ───────────────────
        bm_data = BlackMarketController(user).get_tab_data()
        black_market = {
            'total_professionals': bm_data['total_professionals'],
            'max_professionals': bm_data['max_professionals'],
            'drugs': [
                {
                    'drug_type': drug_type,
                    'name': drug_type.capitalize(),
                    'stash_qty': row['stash_qty'],
                    'current_price': row['current_price'],
                }
                for drug_type, row in bm_data['drug_rows'].items()
                if row['unlocked']
            ],
        }

        data.update({
            'kills': user.kills,
            'heal_cost_per_point': HOSPITAL_HEAL_COST_PER_POINT,
            'items_by_city': items_by_city,
            'guns': guns,
            'airplanes': airplanes,
            'black_market': black_market,
            'missions': MissionsController(user).get_missions_tab_data(),
            'skills_cooldowns': SkillsController(user).get_skills_tab_data(),
        })

        return data
