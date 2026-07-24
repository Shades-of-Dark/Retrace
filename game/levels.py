"""Registry of the game's levels.

Each entry pairs a playable level file with the death-scene file that plays
right before it. To add a level: drop its tilemap JSON (and death-scene
JSON) under game/assets/levels, then add a dict here. main.py drives
level selection entirely off this list instead of hardcoding paths, so
nothing else needs to change to add a level.



"""

LEVELS = [
    {
        "level_path": "game/assets/levels/level_1.json",
        "tilesets_dir": "game/assets/images/tilesets",
        "death_path": "game/assets/levels/death_1.json",
        "death_tilesets_dir": "game/assets/images/tilesets",
    },
]


def get_level(index):
    """The LEVELS entry for `index`."""
    return LEVELS[index]
