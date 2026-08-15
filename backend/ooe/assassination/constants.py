SEARCH_COST_CITY = 1
SEARCH_COST_GLOBAL = 5
SEARCH_DURATION_MINUTES = 20

# How long a resolved, successful search stays usable as grounds for an
# attack, counted from the moment the search becomes ready (ready_at).
SEARCH_VALIDITY_MINUTES = 20

# Attack cooldown, keyed by whether the target died in the attacker's last
# attempt. Based on the attacker's most recent Kill row rather than a cache
# key so it survives cache restarts — the stakes (permadeath) are too high
# to risk losing the cooldown to an evicted cache entry.
ATTACK_COOLDOWN_SUCCESS_HOURS = 10
ATTACK_COOLDOWN_FAIL_HOURS = 1.5

# Fraction of the victim's money_cash transferred to the killer on a clean
# kill (not on mutual elimination — nobody survives to collect it there).
KILL_LOOT_PERCENT = 0.05
