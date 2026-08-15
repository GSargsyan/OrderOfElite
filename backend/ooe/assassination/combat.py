"""
Combat resolution engine — ported from the kill_simulator.py design tool
(repo root, v3). Kept deliberately free of any Django/DB dependency and in
one place, since this is the balance-tuning surface: every knob the game
gets rebalanced by lives in the constants below.

Gear (gun/car/house) is NOT modeled here directly — callers pass in
*effective* (gear-and-Citadel-multiplied) skill points via
User.get_effective_stats(), which already folds in every multiplier
source. This replaces kill_simulator.py's separate CITADEL_SHIFT term
entirely: the only Citadel effect on combat is the existing 10x
defense-point multiplier (ooe.citadel.constants.CITADEL_DEFENSE_MULTIPLIER),
already baked into the number by the time it reaches this module.

See kill_simulator.py for the original scenario-matrix / tuning tool this
was migrated from — it's handy for sanity-checking a constant change
before touching these.
"""
import math
import random

# --- Skill ---
# EffSkill = (skill + OFFSET) ^ EXP. EXP < 1 gives diminishing returns.
SKILL_OFFSET = 30
SKILL_EXP = 0.8

# --- Rank ---
# Each rank of difference shifts dominance by RANK_STEP (log2).
RANK_STEP = 0.18

# --- Budget (attacker only) ---
# Reference "decent" budget doubles every 2 ranks: W(rank) = BASE * 2^(rank/2)
BUDGET_REF_BASE = 1000
BUDGET_POS_CAP = 1.05
BUDGET_POS_SOFT = 2.2
BUDGET_NEG_SLOPE = 1.5

# A broke attempt is half-hearted: backfire chance is multiplied by a
# commit factor that fades against a heavily dominant defender, and
# incoming damage is reduced too (a broke attacker engages less).
BF_COMMIT_W = 1.6
COMMIT_FADE_K = 1.2
COMMIT_FADE_CENTER = 2.0
EXPOSURE_W = 0.7

# Defenders only maul the attacker badly once clearly dominant.
DMG_IN_SHIFT = 0.4

# --- Health ---
# Outgoing power multiplier at hp: q = FLOOR + (1-FLOOR) * hp/100.
HP_POWER_FLOOR = 0.35
# Extra shift on the clean-hit roll against a wounded target (finisher).
FINISHER_SHIFT = 0.6

# --- Randomness ---
NOISE_RANGE = 0.25        # per-roll dominance noise (log2)
DMG_SIGMA = 0.5           # lognormal damage spread (median-centered)

# --- Kill / backfire curves ---
# chance = floor + (ceil-floor) * [ (1-TW)*sig(k*(A-c)) + TW*sig(TK*(A-c)) ]
TAIL_WEIGHT = 0.10
TAIL_K = 0.45

REGULAR = 'regular'
DRIVEBY = 'driveby'
SNIPING = 'sniping'
ATTACK_TYPES = (REGULAR, DRIVEBY, SNIPING)
ATTACK_TYPE_CHOICES = [(REGULAR, 'Regular'), (DRIVEBY, 'Drive-by'), (SNIPING, 'Long Range Sniping')]

KILL_PARAMS = {
    REGULAR: {'center': 1.05, 'k': 2.0, 'floor': 0.0010, 'ceil': 0.995},
    DRIVEBY: {'center': 1.50, 'k': 2.0, 'floor': 0.0008, 'ceil': 0.990},
    SNIPING: {'center': 1.95, 'k': 2.0, 'floor': 0.0005, 'ceil': 0.985},
}
BACKFIRE_PARAMS = {
    REGULAR: {'center': 1.80, 'k': 2.4, 'floor': 0.0010, 'ceil': 0.97},
    DRIVEBY: {'center': 2.00, 'k': 2.4, 'floor': 0.0005, 'ceil': 0.85},
    SNIPING: {'center': 2.50, 'k': 2.4, 'floor': 0.0002, 'ceil': 0.40},
}

# --- Damage (percent of full HP, before noise) ---
DMG_CURVE = {'center': 0.7, 'k': 1.1, 'floor': 0.03, 'ceil': 0.95}
DMG_TO_DEFENDER = {REGULAR: 1.00, DRIVEBY: 0.85, SNIPING: 0.45}
DMG_TO_ATTACKER = {REGULAR: 1.00, DRIVEBY: 0.60, SNIPING: 0.25}

KILL = 'kill'
BACKFIRE = 'backfire'
MUTUAL = 'mutual'
SURVIVE = 'survive'


def _sigmoid(x):
    x = max(-30.0, min(30.0, x))
    return 1.0 / (1.0 + math.exp(-x))


def _effective_skill(points):
    return (points + SKILL_OFFSET) ** SKILL_EXP


def _budget_reference(rank):
    return BUDGET_REF_BASE * 2.0 ** (rank / 2.0)


def _budget_advantage(budget, rank):
    x = math.log2(1.0 + budget / _budget_reference(rank)) - 1.0
    if x >= 0:
        return BUDGET_POS_CAP * math.tanh(x / BUDGET_POS_SOFT)
    return BUDGET_NEG_SLOPE * x


def _hp_quality(hp):
    return HP_POWER_FLOOR + (1.0 - HP_POWER_FLOOR) * hp / 100.0


def _advantage_components(attacker, defender):
    """Log2 components of the attacker's dominance."""
    return {
        'skill': math.log2(_effective_skill(attacker['skill'])
                            / _effective_skill(defender['skill'])),
        'rank': (attacker['rank'] - defender['rank']) * RANK_STEP,
        'budget': _budget_advantage(attacker['budget'], attacker['rank']),
    }


def _curve(params, adv):
    main = _sigmoid(params['k'] * (adv - params['center']))
    tail = _sigmoid(TAIL_K * (adv - params['center']))
    raw = (1.0 - TAIL_WEIGHT) * main + TAIL_WEIGHT * tail
    return params['floor'] + (params['ceil'] - params['floor']) * raw


def _dmg_fraction(adv):
    p = DMG_CURVE
    raw = _sigmoid(p['k'] * (adv - p['center']))
    return p['floor'] + (p['ceil'] - p['floor']) * raw


def _dmg_noise():
    return math.exp(random.gauss(-DMG_SIGMA ** 2 / 2.0, DMG_SIGMA))


def _battle_state(attacker, defender):
    """Everything one live attempt needs, computed once."""
    parts = _advantage_components(attacker, defender)
    a_pow = sum(parts.values())                       # attacker dominance
    d_dom = -(parts['skill'] + parts['rank'])          # defender dominance (mirror)
    qa = math.log2(_hp_quality(attacker['hp']))
    qd = math.log2(_hp_quality(defender['hp']))
    commit = 2.0 ** (BF_COMMIT_W * min(parts['budget'], 0.0))
    commit += (1.0 - commit) * _sigmoid(COMMIT_FADE_K * (d_dom - COMMIT_FADE_CENTER))
    exposure = EXPOSURE_W * min(parts['budget'], 0.0)
    return {
        # Clean-hit roll vs defender / damage dealt to defender:
        'kill_adv': a_pow + qa + FINISHER_SHIFT * (1 - defender['hp'] / 100.0),
        'dmg_out_adv': a_pow + qa,
        # Counter roll vs attacker / damage dealt to attacker:
        'bf_adv': d_dom + qd + FINISHER_SHIFT * (1 - attacker['hp'] / 100.0),
        'dmg_in_adv': d_dom + qd + exposure - DMG_IN_SHIFT,
        'commit': commit,
    }


def resolve_attack(attacker, defender, attack_type):
    """
    Resolves one live attack attempt.

    attacker: {'rank': int, 'skill': int, 'hp': int, 'budget': int}
    defender: {'rank': int, 'skill': int, 'hp': int}
    'skill' should already be the gear/Citadel-adjusted effective stat
    (attacker's effective attack, defender's effective defense).

    Returns {'outcome': 'kill'|'backfire'|'mutual'|'survive',
             'attacker_hp_after': int, 'defender_hp_after': int}.
    Health is only ever reported as 0 when that side actually died this
    attempt — survivors never drop below 1.
    """
    if attack_type not in ATTACK_TYPES:
        raise ValueError(f'Unknown attack type: {attack_type}')

    st = _battle_state(attacker, defender)
    n1 = random.uniform(-NOISE_RANGE, NOISE_RANGE)
    n2 = random.uniform(-NOISE_RANGE, NOISE_RANGE)

    p_kill = _curve(KILL_PARAMS[attack_type], st['kill_adv'] + n1)
    p_bf = _curve(BACKFIRE_PARAMS[attack_type], st['bf_adv'] + n2) * st['commit']

    dmg_def = min(100.0, 100.0 * _dmg_fraction(st['dmg_out_adv'] + n1)
                  * DMG_TO_DEFENDER[attack_type] * _dmg_noise())
    dmg_atk = min(100.0, 100.0 * _dmg_fraction(st['dmg_in_adv'] + n2)
                  * DMG_TO_ATTACKER[attack_type] * _dmg_noise())

    def_dies = random.random() < p_kill or defender['hp'] - dmg_def <= 0
    atk_dies = random.random() < p_bf or attacker['hp'] - dmg_atk <= 0

    def_hp_after = 0 if def_dies else max(1, round(defender['hp'] - dmg_def))
    atk_hp_after = 0 if atk_dies else max(1, round(attacker['hp'] - dmg_atk))

    outcome = {
        (True, True): MUTUAL,
        (True, False): KILL,
        (False, True): BACKFIRE,
        (False, False): SURVIVE,
    }[(def_dies, atk_dies)]

    return {
        'outcome': outcome,
        'attacker_hp_after': atk_hp_after,
        'defender_hp_after': def_hp_after,
    }
