# solo missions startable via start_mission/<name> (party missions have their own flow)
SIMPLE_MISSIONS = ('stakeout', 'recon_op')

RANK_REQUIREMENTS = {
    'stakeout': 1,
    'recon_op': 2,
    'exfiltration': 5,
    'hvt': 8,
}

MISSIONS = {
    'stakeout': {
        'name': 'Stakeout',
        'cooldown': 360, # 6 minutes
        'exp_reward': 10,
        'max_reward_rank': 6,
        'min_reward': 0,
        'max_reward': 1100,
        'random_range': 100,
    },
    'recon_op': {
        'name': 'Recon Op',
        'cooldown': 1200,  # 20 minutes
        'exp_reward': 20,
        'max_reward_rank': 10,
        'min_reward': 10000,
        'max_reward': 20000,
        'random_range': 500,
    },
}

# How long a started party mission takes to resolve — from Start to the
# Claim button appearing. During this window participants may attempt an
# assassination on one another without a prior Search (see
# AssassinationController._on_shared_active_mission).
MISSION_RESOLUTION_SECONDS = 300  # 5 minutes

# Multiplayer missions: lobby (invite/accept/ready per role) -> start ->
# MISSION_RESOLUTION_SECONDS later -> claim. `roles` describes every
# non-Initiator seat: how many slots it has, and what kind of item (a
# UserCar or UserGun key) filling that seat consumes on start.
PARTY_MISSIONS = {
    'exfiltration': {
        'name': 'Exfiltration',
        'cooldown': 7200,  # 2 hours, applies to every participant
        'exp_reward': 150,  # every participant
        'reward': 100000,  # flat for now, goes to the Initiator
        'invite_ttl': 600,  # invitations expire after 10 minutes
        'roles': {
            'driver': {'slots': 1, 'item_type': 'car'},
        },
    },
    'hvt': {
        'name': 'High-Profile Target Operation',
        'cooldown': 28800,  # 8 hours, applies to every participant
        'exp_reward': 480,  # every participant
        'min_reward': 500000,  # random range for now, goes to the Initiator
        'max_reward': 2000000,
        'invite_ttl': 600,  # invitations expire after 10 minutes
        'roles': {
            'driver': {'slots': 1, 'item_type': 'car'},
            'assassin': {'slots': 2, 'item_type': 'gun'},
        },
    },
}
