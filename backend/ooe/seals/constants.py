from ooe.base.events import EventTypes

# ── Anti-abuse caps ───────────────────────────────────────────
SEAL_RAW_TEXT_MAX_LEN = 400
SEAL_MAX_CLAUSES = 3
SEAL_DEADLINE_MIN_DAYS = 1
SEAL_DEADLINE_MAX_DAYS = 30
# A clause whose trigger never fires lapses this many days after signing.
SEAL_TRIGGER_WINDOW_DAYS = 30
# Unsigned seals expire after this long.
SEAL_SIGNATURE_EXPIRY_HOURS = 72
# Compiled drafts never sent are discarded after this long.
SEAL_DRAFT_EXPIRY_HOURS = 1

SEAL_COMPILE_RATE_LIMIT = 5          # compilations per hour per user
SEAL_MAX_PENDING_SENT = 5            # unsigned seals a creator may have out
SEAL_MAX_ACTIVE_PER_USER = 10        # active seals a player may be party to

# Persona non grata durations the creator may choose from
PNG_PENALTY_DAYS_CHOICES = [3, 7, 14, 30]

# ── Vocabulary ────────────────────────────────────────────────
PARTY_REFS = ['party_a', 'party_b']
ITEM_TYPES = ['car', 'house', 'airplane']
SKILLS = ['attack', 'defense', 'driving']

# predicate -> GameEvent event_type it is checked against
TRIGGER_PREDICATES = {
    'IMMEDIATE': None,
    'TIME_REACHED': None,
    'TRAVELED_TO_CITY': EventTypes.TRAVELED_TO_CITY,
    'ENTERED_CITADEL': EventTypes.ENTERED_CITADEL,
    'LEFT_CITADEL': EventTypes.LEFT_CITADEL,
    'ITEM_BOUGHT': EventTypes.ITEM_BOUGHT,
    'ITEM_SOLD': EventTypes.ITEM_SOLD,
    'SKILL_REACHED': EventTypes.SKILL_TRAINED,
}

OBLIGATION_PREDICATES = {
    'TRAVEL_TO': EventTypes.TRAVELED_TO_CITY,
    'AVOID_CITY': EventTypes.TRAVELED_TO_CITY,   # negative
    'BUY_ITEM': EventTypes.ITEM_BOUGHT,
    'SELL_ITEM': EventTypes.ITEM_SOLD,
    'REACH_SKILL': EventTypes.SKILL_TRAINED,
}

# Obligations that are breached by a matching event instead of fulfilled
NEGATIVE_OBLIGATIONS = ['AVOID_CITY']

# ── Compile failure messages ─────────────────────────────────
# Deliberately abstract: the player is never told what sits behind
# the compilation, only that the terms could not be bound.
COMPILE_ERROR_MESSAGES = {
    'VAGUE': 'The terms are too vague to bind. State exact actions and exact places.',
    'UNSUPPORTED': 'These terms cannot be enforced under a Seal.',
    'COMPLEX': 'The terms are too intricate to bind. State them more plainly.',
    'UNKNOWN_PARTY': 'A named party could not be identified.',
    'DEFAULT': 'The terms could not be bound. Rephrase and present them again.',
}

SEAL_HELP_TEXT = (
    'Seals (John Wick Marker equivalent) are promises between 2 Elites. '
    'Failure to fulfill a bound Seal will tag you as a Persona-non-grata and '
    'permanently mark your record as Seal-breaker. Once a Seal is drafted, '
    'it will be sent to the other party to review and sign.'
)
