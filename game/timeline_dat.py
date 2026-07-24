"""Registry of the game's timeline content.

Each entry pairs a playable level time event with the level. To add a level: drop its tilemap JSON (and death-scene
JSON) under game/assets/levels, then add a dict here. main.py drives
timeline creation  entirely off this list instead of hardcoding paths, so
nothing else needs to change to add a timeline event.



"""

TIMELINE_CONTS = [
    {
        "events": [{"age": 5,
                    "total_age": 5,
                    "event_type": "memory",
                    # Where clicking this circle should teleport the player.
                    # Leave both unset to fall back to the timeline's
                    # default next_state/pop behavior instead.
                    "level_path": "game/assets/levels/level_1.json",
                    "tilesets_dir": "game/assets/images/tilesets",
                    },
                   ]

    },
]


def get_timeline_stuff(level):
    return TIMELINE_CONTS[level]
