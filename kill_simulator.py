"""
=============================================================================
  ORDER OF ELITES -- Kill Mechanics Simulator (v3, health-centric)
=============================================================================
  HOW TO USE:
    1. Edit SECTION 1 (the matchup) and run:   python kill_simulator.py
    2. python kill_simulator.py --scenarios    (preset matrix + tuning demos)

  DESIGN (v3):
    Gear multipliers (gun / car / house) are REMOVED from the model: they are
    expected to roughly offset each other and will be tuned separately before
    release. The Citadel remains, because nothing on the attacker's side
    offsets it. Four factors drive everything: SKILL, RANK, BUDGET, HEALTH.

    Every attempt is a SIMULTANEOUS exchange:
      1. Skill, rank, budget and citadel produce a log2 dominance A
         (A = +1 -> attacker effectively twice as strong).
      2. The attempt ALWAYS deals damage both ways. Health is the core
         resource: every attempt chips it, so several attackers (or repeated
         attempts) will grind any target down to 0 even when single-attempt
         kill odds are low.
      3. Each side dies if (a) an instant-kill roll succeeds ("clean hit"),
         OR (b) the damage they take meets or exceeds their CURRENT health.
      4. Both sides resolve TOGETHER: a 1-HP attacker will usually die in
         the exchange even when the target dies too (mutual elimination).

    Health effects:
      - Wounded fighters fight worse: outgoing power scales down to
        HP_POWER_FLOOR (35%) at 0 HP.
      - Wounded targets convert to kills easier: damage threshold is their
        current HP, plus a small "finisher" shift on the clean-hit roll.
      - Net effect: a target at 50% HP is roughly TWICE as likely to die as
        at 100%; at ~20% HP death is likely; at 1 HP it is near-certain.

    Backfire logic:
      - Driven by the DEFENDER's dominance (mirror of the kill logic).
      - In an even match backfire sits clearly BELOW the kill chance;
        it crosses over when the attacker is slightly outmatched, and
        becomes dominant when the attacker is heavily outmatched.
      - A poorly funded attempt is treated as half-hearted: it lowers the
        kill chance AND the exposure (commit factor), so a broke attacker
        fails quietly instead of dying more than an equally matched one.

    Budget:
      - Judged RELATIVE to rank-expected wealth W(rank) = $1k * 2^(rank/2)
        (rank 12 -> ~$64k "decent", rank 25 -> ~$5.8M, rank 30 -> ~$33M).
      - Saturates: past the realistic economy ceiling (~$1-2B) extra money
        buys nothing. $10B is not meaningfully deadlier than $2B.
=============================================================================
"""

import math
import random
import sys

# =============================================================================
# SECTION 1: SCENARIO -- Change these to test different matchups
# =============================================================================

ATTACK_TYPE = "regular"            # "regular", "driveby", "sniping"

# --- ATTACKER ---
ATTACKER_RANK = 14
ATTACKER_ATTACK_SKILL = 850        # Raw attack skill points
ATTACKER_HEALTH = 100              # Current health (1-100)
ATTACKER_OPERATIONAL_BUDGET = 200_000

# --- DEFENDER ---
DEFENDER_RANK = 12
DEFENDER_DEFENSE_SKILL = 600       # Raw defense skill points
DEFENDER_HEALTH = 100              # Current health (1-100)
DEFENDER_IN_CITADEL = False

N_TRIALS = 2000                    # Monte-Carlo sample size

# =============================================================================
# SECTION 2: FORMULA CONSTANTS (the tuning knobs)
# =============================================================================

# --- Skill ---
# EffSkill = (skill + OFFSET) ^ EXP.  EXP < 1 gives diminishing returns while
# keeping ratios meaningful: 4x raw skill ~= 2^1.6 = 3x effective power,
# which in the low-chance region translates to roughly 3-4x kill chance.
SKILL_OFFSET = 30
SKILL_EXP = 0.8

# --- Rank ---
# Each rank of difference shifts dominance by RANK_STEP (log2).
# 0.18 -> +5 ranks ~= 1.9x power, +29 ranks (max gap) ~= 37x power.
RANK_STEP = 0.18

# --- Budget (attacker only) ---
# Reference "decent" budget doubles every 2 ranks: W(rank) = BASE * 2^(rank/2)
#   rank 5 -> $5.7k | rank 12 -> $64k | rank 20 -> $1.0M | rank 30 -> $33M
# x = log2(1 + budget/W) - 1   (0 at a decent budget, -1 at $0)
#   x > 0: budget_adv = POS_CAP * tanh(x / POS_SOFT)   (saturates ~ $1-2B)
#   x < 0: budget_adv = NEG_SLOPE * x                  (feeble attempt)
BUDGET_REF_BASE = 1000
BUDGET_POS_CAP = 1.05
BUDGET_POS_SOFT = 2.2
BUDGET_NEG_SLOPE = 1.5

# A broke attempt is half-hearted: backfire chance is multiplied by
# commit = 2^(COMMIT_W * min(budget_adv, 0)).  High budget never raises
# backfire. The discount FADES against dominant defenders (walking broke
# into the Citadel is suicide regardless of how timid the attempt was):
#   commit_eff = commit + (1-commit) * sig(FADE_K * (def_dominance - FADE_C))
# A broke attempt also engages less, so incoming damage is reduced too
# (EXPOSURE_W shifts the incoming-damage curve down).
BF_COMMIT_W = 1.6
COMMIT_FADE_K = 1.2
COMMIT_FADE_CENTER = 2.0
EXPOSURE_W = 0.7

# Defenders only maul the attacker badly once they are CLEARLY dominant:
# the incoming-damage curve is shifted by this much (log2).
DMG_IN_SHIFT = 0.4

# --- Citadel ---
# Kill side: attacker dominance shifted down by CITADEL_SHIFT (log2).
# Backfire side: counter-lethality uses a reduced weight (walls protect
# better than they kill).
CITADEL_SHIFT = 3.0
CITADEL_BF_WEIGHT = 0.6

# --- Health ---
# Outgoing power multiplier at hp: q = FLOOR + (1-FLOOR) * hp/100.
HP_POWER_FLOOR = 0.35
# Extra shift on the clean-hit roll against a wounded target (finisher).
FINISHER_SHIFT = 0.6

# --- Randomness ---
NOISE_RANGE = 0.25        # per-roll dominance noise (log2)
DMG_SIGMA = 0.5           # lognormal damage spread (median-centered)

# --- Kill / backfire curves ---
# chance = floor + (ceil - floor) * [ (1-TW)*sig(k*(A-c)) + TW*sig(TK*(A-c)) ]
# The second, gentle slope (TAIL) keeps deep-underdog chances at ~0.5-2%
# instead of a flat zero, without touching the mid-range.
TAIL_WEIGHT = 0.10
TAIL_K = 0.45

KILL_PARAMS = {
    "regular": {"center": 1.05, "k": 2.0, "floor": 0.0010, "ceil": 0.995},
    "driveby": {"center": 1.50, "k": 2.0, "floor": 0.0008, "ceil": 0.990},
    "sniping": {"center": 1.95, "k": 2.0, "floor": 0.0005, "ceil": 0.985},
}
BACKFIRE_PARAMS = {
    "regular": {"center": 1.80, "k": 2.4, "floor": 0.0010, "ceil": 0.97},
    "driveby": {"center": 2.00, "k": 2.4, "floor": 0.0005, "ceil": 0.85},
    "sniping": {"center": 2.50, "k": 2.4, "floor": 0.0002, "ceil": 0.40},
}

# --- Damage (percent of full HP, before noise) ---
# dmg_frac = floor + (ceil-floor) * sig(k * (A - center)); dmg = 100*frac*mult
DMG_CURVE = {"center": 0.7, "k": 1.1, "floor": 0.03, "ceil": 0.95}
DMG_TO_DEFENDER = {"regular": 1.00, "driveby": 0.85, "sniping": 0.45}
DMG_TO_ATTACKER = {"regular": 1.00, "driveby": 0.60, "sniping": 0.25}

# =============================================================================
# SECTION 3: THE MATH
# =============================================================================

def sigmoid(x):
    x = max(-30.0, min(30.0, x))
    return 1.0 / (1.0 + math.exp(-x))


def effective_skill(points):
    return (points + SKILL_OFFSET) ** SKILL_EXP


def budget_reference(rank):
    return BUDGET_REF_BASE * 2.0 ** (rank / 2.0)


def budget_advantage(budget, rank):
    x = math.log2(1.0 + budget / budget_reference(rank)) - 1.0
    if x >= 0:
        return BUDGET_POS_CAP * math.tanh(x / BUDGET_POS_SOFT)
    return BUDGET_NEG_SLOPE * x


def hp_quality(hp):
    """Outgoing-power multiplier for a wounded fighter (log2 of this
    is added to their dominance)."""
    return HP_POWER_FLOOR + (1.0 - HP_POWER_FLOOR) * hp / 100.0


def advantage_components(attacker, defender):
    """Log2 components of the attacker's dominance."""
    cit = CITADEL_SHIFT if defender["citadel"] else 0.0
    return {
        "skill": math.log2(effective_skill(attacker["skill"])
                           / effective_skill(defender["skill"])),
        "rank": (attacker["rank"] - defender["rank"]) * RANK_STEP,
        "budget": budget_advantage(attacker["budget"], attacker["rank"]),
        "citadel": -cit,
    }


def curve(params, adv):
    main = sigmoid(params["k"] * (adv - params["center"]))
    tail = sigmoid(TAIL_K * (adv - params["center"]))
    raw = (1.0 - TAIL_WEIGHT) * main + TAIL_WEIGHT * tail
    return params["floor"] + (params["ceil"] - params["floor"]) * raw


def dmg_fraction(adv):
    p = DMG_CURVE
    raw = sigmoid(p["k"] * (adv - p["center"]))
    return p["floor"] + (p["ceil"] - p["floor"]) * raw


def battle_state(attacker, defender):
    """Everything both resolution paths need, computed once."""
    parts = advantage_components(attacker, defender)
    a_pow = sum(parts.values())                       # attacker dominance
    d_dom = -(parts["skill"] + parts["rank"]) \
        + CITADEL_BF_WEIGHT * (-parts["citadel"])     # defender dominance
    qa = math.log2(hp_quality(attacker["hp"]))
    qd = math.log2(hp_quality(defender["hp"]))
    commit = 2.0 ** (BF_COMMIT_W * min(parts["budget"], 0.0))
    commit += (1.0 - commit) * sigmoid(COMMIT_FADE_K * (d_dom - COMMIT_FADE_CENTER))
    exposure = EXPOSURE_W * min(parts["budget"], 0.0)
    return {
        "parts": parts,
        # Clean-hit roll vs defender / damage dealt to defender:
        "kill_adv": a_pow + qa + FINISHER_SHIFT * (1 - defender["hp"] / 100.0),
        "dmg_out_adv": a_pow + qa,
        # Counter roll vs attacker / damage dealt to attacker:
        "bf_adv": d_dom + qd + FINISHER_SHIFT * (1 - attacker["hp"] / 100.0),
        "dmg_in_adv": d_dom + qd + exposure - DMG_IN_SHIFT,
        "commit": commit,
    }


def lognorm_sf(threshold_ratio):
    """P(eps >= t) for a median-1 lognormal with sigma DMG_SIGMA,
    normalized to mean 1."""
    if threshold_ratio <= 0:
        return 1.0
    z = (math.log(threshold_ratio) + DMG_SIGMA ** 2 / 2.0) \
        / (DMG_SIGMA * math.sqrt(2.0))
    return 0.5 * math.erfc(z)


def dmg_noise():
    return math.exp(random.gauss(-DMG_SIGMA ** 2 / 2.0, DMG_SIGMA))


_NOISE_GRID = [-0.2, -0.1, 0.0, 0.1, 0.2]


def analytic(attacker, defender, attack_type):
    """Closed-form probabilities (averaged over the noise grid):
    P(defender dies), P(attacker dies), expected damage both ways."""
    st = battle_state(attacker, defender)
    p_def = p_atk = e_dmg_def = e_dmg_atk = 0.0
    for n in _NOISE_GRID:
        pk = curve(KILL_PARAMS[attack_type], st["kill_adv"] + n)
        mean_out = min(100.0, 100.0 * dmg_fraction(st["dmg_out_adv"] + n)
                       * DMG_TO_DEFENDER[attack_type])
        p_def += pk + (1 - pk) * lognorm_sf(defender["hp"] / mean_out)
        e_dmg_def += mean_out

        pb = curve(BACKFIRE_PARAMS[attack_type], st["bf_adv"] + n) * st["commit"]
        mean_in = min(100.0, 100.0 * dmg_fraction(st["dmg_in_adv"] + n)
                      * DMG_TO_ATTACKER[attack_type])
        p_atk += pb + (1 - pb) * lognorm_sf(attacker["hp"] / mean_in)
        e_dmg_atk += mean_in
    g = len(_NOISE_GRID)
    return {"p_def_death": p_def / g, "p_atk_death": p_atk / g,
            "e_dmg_def": e_dmg_def / g, "e_dmg_atk": e_dmg_atk / g,
            "state": st}


def simulate_once(attacker, defender, attack_type, state=None):
    """One attempt. Returns (outcome, atk_hp_after, def_hp_after).
    outcome: 'kill' | 'backfire' | 'mutual' | 'survive'"""
    st = state or battle_state(attacker, defender)
    n1 = random.uniform(-NOISE_RANGE, NOISE_RANGE)
    n2 = random.uniform(-NOISE_RANGE, NOISE_RANGE)

    p_kill = curve(KILL_PARAMS[attack_type], st["kill_adv"] + n1)
    p_bf = curve(BACKFIRE_PARAMS[attack_type], st["bf_adv"] + n2) * st["commit"]

    dmg_def = min(100.0, 100.0 * dmg_fraction(st["dmg_out_adv"] + n1)
                  * DMG_TO_DEFENDER[attack_type] * dmg_noise())
    dmg_atk = min(100.0, 100.0 * dmg_fraction(st["dmg_in_adv"] + n2)
                  * DMG_TO_ATTACKER[attack_type] * dmg_noise())

    def_dies = random.random() < p_kill or defender["hp"] - dmg_def <= 0
    atk_dies = random.random() < p_bf or attacker["hp"] - dmg_atk <= 0

    def_hp_after = 0 if def_dies else max(1.0, defender["hp"] - dmg_def)
    atk_hp_after = 0 if atk_dies else max(1.0, attacker["hp"] - dmg_atk)
    outcome = {(True, True): "mutual", (True, False): "kill",
               (False, True): "backfire", (False, False): "survive"}[
                   (def_dies, atk_dies)]
    return outcome, atk_hp_after, def_hp_after


def monte_carlo(attacker, defender, attack_type, n_trials):
    st = battle_state(attacker, defender)
    out = {"kill": 0, "backfire": 0, "mutual": 0, "survive": 0}
    hp_atk, hp_def = [], []
    for _ in range(n_trials):
        result, a_hp, d_hp = simulate_once(attacker, defender, attack_type, st)
        out[result] += 1
        if result == "survive":
            hp_atk.append(a_hp)
            hp_def.append(d_hp)
    avg = lambda xs: sum(xs) / len(xs) if xs else None
    return out, avg(hp_atk), avg(hp_def)


# =============================================================================
# SECTION 4: REPORTING
# =============================================================================

def _mk_attacker(rank, skill, budget, hp=100):
    return dict(rank=rank, skill=skill, hp=hp, budget=budget)


def _mk_defender(rank, skill, citadel=False, hp=100):
    return dict(rank=rank, skill=skill, hp=hp, citadel=citadel)


def print_scenario_line(label, attacker, defender, attack_type, n_trials=2000):
    print("-" * 92)
    print(f"  SCENARIO: {label}  [{attack_type}]")
    print(f"    Attacker: rank={attacker['rank']} skill={attacker['skill']} "
          f"hp={attacker['hp']}% budget=${attacker['budget']:,}")
    print(f"    Defender: rank={defender['rank']} skill={defender['skill']} "
          f"hp={defender['hp']}% citadel="
          f"{'YES' if defender['citadel'] else 'No'}")

    res = analytic(attacker, defender, attack_type)
    parts = res["state"]["parts"]
    comp = " | ".join(f"{k} {v:+.2f}" for k, v in parts.items())
    print(f"    Advantage: {comp}  ->  A={sum(parts.values()):+.2f}")
    print(f"    Analytic ({attack_type}): target dies {res['p_def_death']*100:.1f}% | "
          f"attacker dies {res['p_atk_death']*100:.1f}% | "
          f"avg dmg -> target {res['e_dmg_def']:.0f} hp, "
          f"attacker {res['e_dmg_atk']:.0f} hp")

    out, a_hp, d_hp = monte_carlo(attacker, defender, attack_type, n_trials)
    pct = lambda k: out[k] / n_trials * 100
    hp_note = ""
    if a_hp is not None:
        hp_note = (f"   (survivors avg HP: attacker {a_hp:.0f}%, "
                   f"target {d_hp:.0f}%)")
    print(f"    Monte-Carlo ({n_trials}x): killed {pct('kill'):.1f}% | "
          f"backfired {pct('backfire'):.1f}% | both die {pct('mutual'):.1f}% | "
          f"both survive {pct('survive'):.1f}%{hp_note}")


def hp_sensitivity_demo(attacker, defender, attack_type, label):
    """P(death) as the DEFENDER's starting HP drops -- shows how wounds
    convert into deaths, for tuning HP_POWER_FLOOR / FINISHER_SHIFT /
    DMG_SIGMA."""
    print("-" * 92)
    print(f"  HP SENSITIVITY -- {label}  [{attack_type}]")
    print(f"    (same matchup, only the listed side's starting HP changes)")
    hps = [100, 75, 50, 35, 20, 10, 1]
    row_d, row_a = [], []
    for hp in hps:
        d = dict(defender, hp=hp)
        row_d.append(analytic(attacker, d, attack_type)["p_def_death"] * 100)
        a = dict(attacker, hp=hp)
        row_a.append(analytic(a, defender, attack_type)["p_atk_death"] * 100)
    print("    Defender HP:      " + "".join(f"{hp:>9}%" for hp in hps))
    print("    P(target dies):   " + "".join(f"{p:>9.1f}" for p in row_d))
    print("    Attacker HP:      " + "".join(f"{hp:>9}%" for hp in hps))
    print("    P(attacker dies): " + "".join(f"{p:>9.1f}" for p in row_a))


def gauntlet_demo(attacker, defender, attack_type, label, n_runs=2000):
    """The multi-attacker grind: fresh full-HP attackers hit the same
    defender until they die. Shows how HP chips down across attempts."""
    print("-" * 92)
    print(f"  GAUNTLET -- {label}  [{attack_type}]")
    print("    Fresh identical attackers strike the same target until it dies.")
    attempts_needed = []
    sample = None
    for run in range(n_runs):
        hp = float(defender["hp"])
        trajectory = [hp]
        for attempt in range(1, 26):
            d = dict(defender, hp=hp)
            outcome, _, d_hp = simulate_once(attacker, d, attack_type)
            hp = d_hp
            trajectory.append(hp)
            if outcome in ("kill", "mutual"):
                attempts_needed.append(attempt)
                break
        else:
            attempts_needed.append(26)
        if sample is None and len(trajectory) >= 3:
            sample = trajectory
    attempts_needed.sort()
    q = lambda p: attempts_needed[int(p * (len(attempts_needed) - 1))]
    print(f"    Attempts until death: median {q(0.5)}, "
          f"25th pct {q(0.25)}, 75th pct {q(0.75)} "
          f"(capped at 25)")
    traj = " -> ".join(f"{h:.0f}" for h in sample)
    print(f"    Sample HP trajectory: {traj}")


def run_report(label, attacker, defender, attack_type, n_trials):
    print("=" * 92)
    print(f"  ORDER OF ELITES -- Kill Simulator | {label}")
    print("=" * 92)
    print_scenario_line(label, attacker, defender, attack_type, n_trials)
    hp_sensitivity_demo(attacker, defender, attack_type, label)
    gauntlet_demo(attacker, defender, attack_type, label)
    # One live roll
    result, a_hp, d_hp = simulate_once(attacker, defender, attack_type)
    print("-" * 92)
    if result == "kill":
        print(f"  THIS RUN: TARGET ELIMINATED. Attacker walks away at {a_hp:.0f}% HP.")
    elif result == "backfire":
        print(f"  THIS RUN: BACKFIRE -- attacker eliminated. Target at {d_hp:.0f}% HP.")
    elif result == "mutual":
        print("  THIS RUN: MUTUAL ELIMINATION -- both parties are dead.")
    else:
        print(f"  THIS RUN: Both survive. Attacker {a_hp:.0f}% HP, "
              f"Target {d_hp:.0f}% HP.")
    print("=" * 92)


def run_scenarios():
    atk, dfn = _mk_attacker, _mk_defender
    scenarios = [
        # --- edge cases ---
        ("Perfectly even match", "regular",
         atk(12, 1000, 100_000), dfn(12, 1000)),
        ("Both at zero stats", "regular",
         atk(1, 0, 0), dfn(1, 0)),
        ("Overwhelming attacker vs bare defender", "sniping",
         atk(30, 50000, 1_000_000_000), dfn(5, 0)),
        ("Bare attacker vs citadel titan", "regular",
         atk(5, 0, 0), dfn(30, 50000, citadel=True)),
        ("Both at 1 HP (near-death duel)", "driveby",
         atk(15, 2000, 500_000, hp=1), dfn(15, 2000, hp=1)),
        ("Finishing blow on 1-HP target", "regular",
         atk(14, 1800, 300_000), dfn(13, 1600, hp=1)),
        ("Desperate 1-HP attacker vs full-HP target", "regular",
         atk(14, 1800, 300_000, hp=1), dfn(13, 1600)),
        ("Extreme rank gap, low attacking high", "sniping",
         atk(1, 500, 100_000), dfn(30, 500)),
        ("Extreme rank gap, high attacking low", "regular",
         atk(30, 500, 100_000), dfn(1, 500)),
        ("Budget saturation: $10B vs broke", "regular",
         atk(18, 5000, 10_000_000_000), dfn(18, 5000)),
        ("Citadel-only difference", "driveby",
         atk(20, 8000, 2_000_000), dfn(20, 8000, citadel=True)),

        # --- realistic cases ---
        ("New player probing (rank 3 vs 5)", "regular",
         atk(3, 150, 5_000), dfn(5, 200)),
        ("Early-game skirmish", "driveby",
         atk(7, 400, 40_000), dfn(6, 350)),
        ("Mid-game rivalry, close skill", "driveby",
         atk(15, 3000, 800_000), dfn(16, 2800)),
        ("Gang war retaliation strike", "regular",
         atk(20, 8000, 2_000_000), dfn(18, 6000)),
        ("Underdog upset attempt", "sniping",
         atk(8, 500, 50_000), dfn(22, 15000)),
        ("Deep pockets vs skill grinder", "regular",
         atk(25, 5000, 50_000_000), dfn(25, 20000)),
        ("Top-rank endgame duel", "sniping",
         atk(30, 20000, 300_000_000), dfn(29, 19000)),
        ("Wounded rival, opportunistic driveby", "driveby",
         atk(17, 4000, 900_000), dfn(17, 4200, hp=20)),
        ("Broke attacker, average defender", "driveby",
         atk(11, 1200, 1_000), dfn(13, 900)),
    ]

    print("=" * 92)
    print("  ORDER OF ELITES -- Kill Simulator | Scenario Matrix (v3)")
    print("=" * 92)
    for label, attack_type, attacker, defender in scenarios:
        print_scenario_line(label, attacker, defender, attack_type)

    # --- tuning demos ---
    print()
    print("=" * 92)
    print("  TUNING DEMOS")
    print("=" * 92)
    even_atk = _mk_attacker(12, 1000, 100_000)
    even_dfn = _mk_defender(12, 1000)
    hp_sensitivity_demo(even_atk, even_dfn, "regular", "Even match (rank 12)")
    gauntlet_demo(even_atk, even_dfn, "regular", "Even match (rank 12)")
    strong_dfn = _mk_defender(14, 3000)
    weak_atk = _mk_attacker(12, 1500, 100_000)
    gauntlet_demo(weak_atk, strong_dfn, "regular",
                  "Outmatched attackers grinding a stronger target")
    print("-" * 92)


if __name__ == "__main__":
    if "--scenarios" in sys.argv:
        run_scenarios()
    else:
        _attacker = _mk_attacker(ATTACKER_RANK, ATTACKER_ATTACK_SKILL,
                                 ATTACKER_OPERATIONAL_BUDGET, ATTACKER_HEALTH)
        _defender = _mk_defender(DEFENDER_RANK, DEFENDER_DEFENSE_SKILL,
                                 DEFENDER_IN_CITADEL, DEFENDER_HEALTH)
        run_report("Custom Matchup", _attacker, _defender,
                   ATTACK_TYPE, N_TRIALS)
