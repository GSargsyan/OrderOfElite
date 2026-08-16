# ── Eligibility / rotation ───────────────────────────────────
COUNCIL_MIN_RANK = 25
COUNCIL_SEATS = 5

# Peer approval / rejection threshold, scaled down when the council has
# fewer than 4 other members: min(COUNCIL_APPROVAL_THRESHOLD_CAP, other_members_count)
COUNCIL_APPROVAL_THRESHOLD_CAP = 3

# ── Consequence choices ──────────────────────────────────────
# Mirrors ooe.seals.constants.PNG_PENALTY_DAYS_CHOICES. Duplicated
# rather than imported across apps since this is UI-facing vocabulary,
# not shared business logic.
PNG_PENALTY_DAYS_CHOICES = [3, 7, 14, 30]

BLACKLIST_BOUNTY_CHOICES = [
    100000, 200000, 500000,
    1000000, 1500000, 2500000,
    5000000, 7500000, 10000000, 15000000,
]

# ── Order of Elite document ──────────────────────────────────
# Fixed document title. Not stored on any model, not part of the
# authoring form - shown to players as the document header only.
ORDER_OF_ELITE_TITLE = 'Order of Elite'

CONDITION_TITLE_MAX_LEN = 120
CONDITION_CONTENT_MAX_LEN = 2000

COUNCIL_CHAT_ROOM_NAME = 'Grand Council'
COUNCIL_CHAT_ROOM_TYPE = 'grand_council'
