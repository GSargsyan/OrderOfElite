"""
=============================================================================
  ORDER OF ELITES -- Kill Mechanics Simulator (v2)
=============================================================================
  HOW TO USE:
    1. Edit SECTION 1 (the matchup) and run:  python kill_simulator.py
    2. Optional: python kill_simulator.py --scenarios   (preset sanity matrix)

  DESIGN:
    Everything is computed in log2 "dominance" space (Advantage, A):
      A = skill_adv + gear_adv + rank_adv + budget_adv + health_shift
    A = 0  -> perfectly even.  A = +2 -> attacker is 4x stronger.  A = -2 -> 4x weaker.

    KillChance     = floor + (ceil - floor) * sigmoid(k * (A - A0))
    BackfireChance = same curve, but driven by the DEFENDER's advantage (-A).

    The centers (A0) sit around 2-3, so an even fight produces ~0.3% kill and
    ~0.6% backfire -> in ~99% of even attempts both walk away wounded.
    Death requires clear dominance (4x+), or a defender strong enough to make
    a regular attempt suicidal. Noise is small (log-space +/-0.15 ~ +/-11%
    power), so repeated runs with the same inputs give stable outcomes.

    Components:
      EffSkill   = (skill + 25) ^ 0.55          (diminishing returns; a
                   50,000-pt veteran is ~8x a 1,000-pt player, not 50x)
      skill_adv  = log2(EffAtk / EffDef)
      gear_adv   = log2(gun x carAtk / (house x carDef x citadel))
      rank_adv   = (atkRank - defRank) * log2(1.10)    (+18 ranks ~ 5.6x)
      budget_adv = log2(1 + log10(1 + budget/100k)), capped at 6x
      health     = wounded target is easier to finish (up to +1.5 A at 0 HP)
=============================================================================
"""

import math
import random
import sys

# =============================================================================
# SECTION 1: SCENARIO -- Change these to test different matchups
# =============================================================================

ATTACK_TYPE = "driveby"            # "regular", "driveby", "sniping"

# --- ATTACKER ---
ATTACKER_RANK = 14
ATTACKER_ATTACK_SKILL = 850       # Raw attack skill points
ATTACKER_HEALTH = 100              # Current health (0-100)
ATTACKER_GUN_MULTIPLIER = 2.0      # 1.0 = B-92 ... 4.0 = Intervention
ATTACKER_CAR_ATTACK_MULT = 1.5     # 1.0 = no car ... 3.5 = Bordeaux V16
ATTACKER_OPERATIONAL_BUDGET = 20_000_000

# --- DEFENDER ---
DEFENDER_RANK = 12
DEFENDER_DEFENSE_SKILL = 10      # Raw defense skill points
DEFENDER_HEALTH = 100              # Current health (0-100)
DEFENDER_HOUSE_DEFENSE_MULT = 1.5  # 1.0 = none, 1.5 Studio, 3.0 Condo, 5.0 Mansion
DEFENDER_CAR_DEFENSE_MULT = 1.5    # 1.0 = no car ... 3.5 = Imperium-R
DEFENDER_IN_CITADEL = False

N_TRIALS = 1000                    # Monte-Carlo sample size for the summary

# =============================================================================
# SECTION 2: FORMULA CONSTANTS
# =============================================================================

# Skill curve: EffSkill = (skill + SKILL_OFFSET) ^ SKILL_EXP
SKILL_OFFSET = 25
SKILL_EXP = 0.55

# Rank: each rank of difference multiplies power by RANK_BASE
RANK_BASE = 1.10

# Budget: factor = 1 + BUDGET_LOG_SCALE * log10(1 + budget / BUDGET_UNIT)
# $100k -> 1.3x | $1M -> 2x | $10M -> 3x | $100M -> 4x | $1B -> 5x | cap 6x
BUDGET_UNIT = 100_000
BUDGET_LOG_SCALE = 1.0
BUDGET_MAX_FACTOR = 6.0

CITADEL_MULTIPLIER = 10

# Wounded-target bonus: advantage shift at 0 HP (scales linearly with lost HP)
HEALTH_MAX_SHIFT = 1.5

# Noise applied to advantage per roll (log2 space). 0.15 ~ +/-11% power swing.
NOISE_RANGE = 0.15

# Kill curves: chance = floor + (ceil-floor) * sigmoid(k * (A - center))
KILL_PARAMS = {
    "regular": {"center": 2.0, "k": 3.5, "floor": 0.002, "ceil": 0.95},
    "driveby": {"center": 2.4, "k": 3.5, "floor": 0.0015, "ceil": 0.85},
    "sniping": {"center": 2.9, "k": 3.5, "floor": 0.001, "ceil": 0.70},
}

# Backfire curves: driven by DEFENDER advantage (-A), attacker HP shift added
BACKFIRE_PARAMS = {
    "regular": {"center": 1.6, "k": 3.0, "floor": 0.001, "ceil": 0.60},
    "driveby": {"center": 2.2, "k": 3.0, "floor": 0.0005, "ceil": 0.35},
    "sniping": {"center": 3.0, "k": 3.0, "floor": 0.0002, "ceil": 0.12},
}

# Damage on a failed attempt (percent HP). Scaled by power ratio.
BASE_DAMAGE = 30
DAMAGE_MULT_DEFENDER = {"regular": 1.4, "driveby": 1.1, "sniping": 1.0}
DAMAGE_MULT_ATTACKER = {"regular": 1.2, "driveby": 0.8, "sniping": 0.3}
DAMAGE_NOISE = 0.20

# =============================================================================
# SECTION 3: THE MATH
# =============================================================================

def sigmoid(x):
    x = max(-30, min(30, x))
    return 1.0 / (1.0 + math.exp(-x))


def effective_skill(points):
    return (points + SKILL_OFFSET) ** SKILL_EXP


def budget_factor(budget):
    factor = 1 + BUDGET_LOG_SCALE * math.log10(1 + budget / BUDGET_UNIT)
    return min(factor, BUDGET_MAX_FACTOR)


def health_shift(hp):
    """Extra advantage against a wounded player (0 at full HP)."""
    return HEALTH_MAX_SHIFT * (1 - hp / 100.0)


def advantage_components(atk_skill, def_skill, gun, car_atk, house, car_def,
                         in_citadel, atk_rank, def_rank, budget):
    """Attacker's log2 dominance, broken into parts (health handled separately)."""
    citadel = CITADEL_MULTIPLIER if in_citadel else 1.0
    return {
        "skill": math.log2(effective_skill(atk_skill) / effective_skill(def_skill)),
        "gear": math.log2((gun * car_atk) / (house * car_def * citadel)),
        "rank": (atk_rank - def_rank) * math.log2(RANK_BASE),
        "budget": math.log2(budget_factor(budget)),
    }


def curve(params, adv):
    raw = sigmoid(params["k"] * (adv - params["center"]))
    return params["floor"] + (params["ceil"] - params["floor"]) * raw


def kill_chance(base_adv, attack_type, defender_hp, noise=0.0):
    return curve(KILL_PARAMS[attack_type], base_adv + health_shift(defender_hp) + noise)


def backfire_chance(base_adv, attack_type, attacker_hp, noise=0.0):
    defender_adv = -base_adv + health_shift(attacker_hp)
    return curve(BACKFIRE_PARAMS[attack_type], defender_adv + noise)


def roll_damage(base_adv, attack_type):
    """(dmg_to_defender, dmg_to_attacker) on a failed attempt."""
    ratio = 2.0 ** base_adv
    noise = lambda: random.uniform(1 - DAMAGE_NOISE, 1 + DAMAGE_NOISE)
    to_def = BASE_DAMAGE * (ratio / (ratio + 1)) * DAMAGE_MULT_DEFENDER[attack_type] * noise()
    to_atk = BASE_DAMAGE * (1 / (ratio + 1)) * DAMAGE_MULT_ATTACKER[attack_type] * noise()
    return max(1, min(65, to_def)), max(0.5, min(65, to_atk))


def simulate_once(base_adv, attack_type, atk_hp, def_hp):
    """Returns (outcome, final_atk_hp, final_def_hp).
    outcome: 'kill' | 'backfire' | 'survive'"""
    noise = random.uniform(-NOISE_RANGE, NOISE_RANGE)
    if random.random() < kill_chance(base_adv, attack_type, def_hp, noise):
        _, to_atk = roll_damage(base_adv, attack_type)
        return "kill", max(1, atk_hp - to_atk * 0.5), 0
    to_def, to_atk = roll_damage(base_adv, attack_type)
    new_def_hp = max(1, def_hp - to_def)
    new_atk_hp = max(1, atk_hp - to_atk)
    bf_noise = random.uniform(-NOISE_RANGE, NOISE_RANGE)
    if random.random() < backfire_chance(base_adv, attack_type, new_atk_hp, bf_noise):
        return "backfire", 0, new_def_hp
    return "survive", new_atk_hp, new_def_hp


# =============================================================================
# SECTION 4: REPORTING
# =============================================================================

def run_report(label, attacker, defender, attack_type, n_trials, full=True):
    """Print a full matchup report for one (attacker, defender) pair.

    attacker: dict with rank, skill, hp, gun, car, budget
    defender: dict with rank, skill, hp, house, car, citadel
    Returns (base_adv, parts) so callers can reuse the numbers.
    """
    parts = advantage_components(
        attacker["skill"], defender["skill"],
        attacker["gun"], attacker["car"],
        defender["house"], defender["car"],
        defender["citadel"], attacker["rank"], defender["rank"],
        attacker["budget"])
    base_adv = sum(parts.values())
    hp_shift = health_shift(defender["hp"])

    print("=" * 64)
    print(f"  ORDER OF ELITES -- Kill Simulator | {label}")
    print("=" * 64)
    print(f"  Attacker: Rank {attacker['rank']} | ATK {attacker['skill']} | "
          f"HP {attacker['hp']}% | Gun x{attacker['gun']} | "
          f"Car x{attacker['car']} | Budget ${attacker['budget']:,}")
    print(f"  Defender: Rank {defender['rank']} | DEF {defender['skill']} | "
          f"HP {defender['hp']}% | House x{defender['house']} | "
          f"Car x{defender['car']} | Citadel: "
          f"{'YES' if defender['citadel'] else 'No'}")
    print("-" * 64)
    comp = " | ".join(f"{name} {val:+.2f}" for name, val in parts.items())
    print(f"  Advantage: {comp}")
    total = base_adv + hp_shift
    print(f"  Total A = {total:+.2f}  (attacker is {2**total:.2f}x "
          f"{'stronger' if total >= 0 else 'weaker'})"
          + (f"  [includes +{hp_shift:.2f} wounded-target bonus]" if hp_shift else ""))
    print("-" * 64)
    print(f"  {'Type':<10}{'Kill %':>10}{'Backfire %':>14}")
    for atype in ("regular", "driveby", "sniping"):
        kc = kill_chance(base_adv, atype, defender["hp"])
        bc = backfire_chance(base_adv, atype, attacker["hp"])
        marker = "  <-- selected" if atype == attack_type else ""
        print(f"  {atype:<10}{kc*100:>9.2f}{bc*100:>13.2f}{marker}")

    if not full:
        print("=" * 64)
        return base_adv, parts

    # Monte-Carlo distribution
    outcomes = {"kill": 0, "backfire": 0, "survive": 0}
    dmg_def, dmg_atk = [], []
    for _ in range(n_trials):
        result, atk_hp, def_hp = simulate_once(
            base_adv, attack_type, attacker["hp"], defender["hp"])
        outcomes[result] += 1
        if result == "survive":
            dmg_def.append(defender["hp"] - def_hp)
            dmg_atk.append(attacker["hp"] - atk_hp)
    print("-" * 64)
    print(f"  {n_trials} simulated '{attack_type}' attempts:")
    print(f"    Target killed:   {outcomes['kill'] / n_trials * 100:6.1f}%")
    print(f"    Attacker killed: {outcomes['backfire'] / n_trials * 100:6.1f}%")
    both = outcomes['survive'] / n_trials * 100
    if dmg_def:
        print(f"    Both survive:    {both:6.1f}%   "
              f"(avg dmg: defender {sum(dmg_def)/len(dmg_def):.1f}%, "
              f"attacker {sum(dmg_atk)/len(dmg_atk):.1f}%)")
    else:
        print(f"    Both survive:    {both:6.1f}%")

    # One live roll
    result, atk_hp, def_hp = simulate_once(
        base_adv, attack_type, attacker["hp"], defender["hp"])
    print("-" * 64)
    if result == "kill":
        print(f"  THIS RUN: TARGET ELIMINATED. Attacker HP {atk_hp:.0f}%.")
    elif result == "backfire":
        print(f"  THIS RUN: BACKFIRE -- attacker eliminated. Defender HP {def_hp:.0f}%.")
    else:
        print(f"  THIS RUN: Both survive. Attacker HP {atk_hp:.0f}%, "
              f"Defender HP {def_hp:.0f}%.")
    print("=" * 64)
    return base_adv, parts


def _scenario_from_globals():
    """Builds the attacker/defender dicts from the SECTION 1 constants above,
    so editing those constants and running with no flags behaves exactly
    like a single custom matchup."""
    attacker = dict(rank=ATTACKER_RANK, skill=ATTACKER_ATTACK_SKILL,
                     hp=ATTACKER_HEALTH, gun=ATTACKER_GUN_MULTIPLIER,
                     car=ATTACKER_CAR_ATTACK_MULT, budget=ATTACKER_OPERATIONAL_BUDGET)
    defender = dict(rank=DEFENDER_RANK, skill=DEFENDER_DEFENSE_SKILL,
                     hp=DEFENDER_HEALTH, house=DEFENDER_HOUSE_DEFENSE_MULT,
                     car=DEFENDER_CAR_DEFENSE_MULT, citadel=DEFENDER_IN_CITADEL)
    return attacker, defender


def print_scenario_line(label, attacker, defender, attack_type, n_trials=400):
    """Compact per-scenario output: full variable dump + one-line results,
    for scanning many matchups at a glance."""
    print("-" * 88)
    print(f"  SCENARIO: {label}  [{attack_type}]")
    print(f"    Attacker: rank={attacker['rank']} skill={attacker['skill']} "
          f"hp={attacker['hp']}% gun=x{attacker['gun']} car=x{attacker['car']} "
          f"budget=${attacker['budget']:,}")
    print(f"    Defender: rank={defender['rank']} skill={defender['skill']} "
          f"hp={defender['hp']}% house=x{defender['house']} car=x{defender['car']} "
          f"citadel={'YES' if defender['citadel'] else 'No'}")

    parts = advantage_components(
        attacker["skill"], defender["skill"],
        attacker["gun"], attacker["car"],
        defender["house"], defender["car"],
        defender["citadel"], attacker["rank"], defender["rank"],
        attacker["budget"])
    base_adv = sum(parts.values())
    comp = " | ".join(f"{name} {val:+.2f}" for name, val in parts.items())
    print(f"    Advantage: {comp}  ->  A={base_adv:+.2f}")

    kills = "/".join(f"{kill_chance(base_adv, t, defender['hp'])*100:.1f}"
                     for t in ("regular", "driveby", "sniping"))
    bfs = "/".join(f"{backfire_chance(base_adv, t, attacker['hp'])*100:.2f}"
                   for t in ("regular", "driveby", "sniping"))
    print(f"    Kill% (reg/drv/snp): {kills}   Backfire% (reg/drv/snp): {bfs}")

    outcomes = {"kill": 0, "backfire": 0, "survive": 0}
    for _ in range(n_trials):
        result, _, _ = simulate_once(base_adv, attack_type, attacker["hp"], defender["hp"])
        outcomes[result] += 1
    print(f"    Monte-Carlo ({n_trials}x '{attack_type}'): "
          f"kill {outcomes['kill']/n_trials*100:.1f}% | "
          f"backfire {outcomes['backfire']/n_trials*100:.1f}% | "
          f"survive {outcomes['survive']/n_trials*100:.1f}%")


def run_scenarios():
    """Preset matchups covering edge cases and moderately realistic cases,
    to sanity-check the curves at a glance."""

    def atk(rank, skill, gun, car, budget, hp=100):
        return dict(rank=rank, skill=skill, hp=hp, gun=gun, car=car, budget=budget)

    def dfn(rank, skill, house, car, citadel=False, hp=100):
        return dict(rank=rank, skill=skill, hp=hp, house=house, car=car, citadel=citadel)

    # label, attack_type, attacker, defender
    scenarios = [
        # --- edge cases ---
        ("Perfectly even match", "regular",
         atk(12, 1000, 1.5, 1.0, 100_000), dfn(12, 1000, 1.5, 1.0)),
        ("Both at zero stats", "regular",
         atk(1, 0, 1.0, 1.0, 0), dfn(1, 0, 1.0, 1.0)),
        ("Max gear attacker vs bare defender", "sniping",
         atk(20, 50000, 4.0, 3.5, 1_000_000_000), dfn(5, 0, 1.0, 1.0)),
        ("Bare attacker vs maxed-out citadel defender", "regular",
         atk(5, 0, 1.0, 1.0, 0), dfn(20, 50000, 5.0, 3.5, citadel=True)),
        ("Both at 1 HP (near-death duel)", "driveby",
         atk(15, 2000, 2.0, 1.5, 500_000, hp=1), dfn(15, 2000, 1.5, 1.5, hp=1)),
        ("Finishing blow on 1-HP target", "regular",
         atk(14, 1800, 1.5, 1.0, 300_000), dfn(13, 1600, 1.5, 1.0, hp=1)),
        ("Desperate 1-HP attacker vs full-HP target", "regular",
         atk(14, 1800, 1.5, 1.0, 300_000, hp=1), dfn(13, 1600, 1.5, 1.0)),
        ("Extreme rank gap, low rank attacking high", "sniping",
         atk(1, 500, 1.5, 1.0, 100_000), dfn(50, 500, 1.5, 1.0)),
        ("Extreme rank gap, high rank attacking low", "regular",
         atk(50, 500, 1.5, 1.0, 100_000), dfn(1, 500, 1.5, 1.0)),
        ("Budget cap test: $10B vs broke", "regular",
         atk(18, 5000, 2.0, 1.5, 10_000_000_000), dfn(18, 5000, 1.5, 1.0)),
        ("Citadel-only difference (same everything else)", "driveby",
         atk(20, 8000, 3.0, 2.0, 2_000_000), dfn(20, 8000, 3.0, 2.0, citadel=True)),

        # --- moderately realistic cases ---
        ("New player probing (rank 3 vs 5)", "regular",
         atk(3, 150, 1.0, 1.0, 5_000), dfn(5, 200, 1.5, 1.0)),
        ("Early-game skirmish", "driveby",
         atk(7, 400, 1.5, 1.0, 40_000), dfn(6, 350, 1.5, 1.0)),
        ("Mid-game rivalry, close skill", "driveby",
         atk(15, 3000, 2.0, 1.5, 800_000), dfn(16, 2800, 2.0, 1.5)),
        ("Gang war retaliation strike", "regular",
         atk(20, 8000, 2.5, 2.0, 2_000_000), dfn(18, 6000, 2.0, 1.5)),
        ("Underdog upset attempt", "sniping",
         atk(8, 500, 1.5, 1.0, 50_000), dfn(22, 15000, 3.0, 2.5)),
        ("Whale gear vs skill grinder", "regular",
         atk(25, 5000, 4.0, 3.5, 50_000_000), dfn(25, 20000, 1.5, 1.0)),
        ("Top-rank endgame duel", "sniping",
         atk(45, 60000, 3.5, 3.0, 300_000_000), dfn(44, 58000, 4.0, 3.0)),
        ("Wounded rival, opportunistic driveby", "driveby",
         atk(17, 4000, 2.0, 1.5, 900_000), dfn(17, 4200, 2.0, 1.5, hp=20)),
        ("Low-budget opportunist vs housed target", "driveby",
         atk(11, 1200, 1.0, 1.0, 15_000), dfn(13, 900, 3.0, 1.0)),
    ]

    print("=" * 88)
    print("  ORDER OF ELITES -- Kill Simulator | Scenario Matrix")
    print("=" * 88)
    for label, attack_type, attacker, defender in scenarios:
        print_scenario_line(label, attacker, defender, attack_type)
    print("-" * 88)


if __name__ == "__main__":
    if "--scenarios" in sys.argv:
        run_scenarios()
    else:
        _attacker, _defender = _scenario_from_globals()
        run_report("Custom Matchup", _attacker, _defender, ATTACK_TYPE, N_TRIALS)
