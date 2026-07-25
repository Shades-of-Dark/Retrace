TIMELINE_CONTS = [
    {
        "total_age": 5,
        "events": [{"age": 5,

                    "event_type": "memory",
                    "level_path": "game/assets/levels/level_1.json",
                    "tilesets_dir": "game/assets/images/tilesets",
                    },
                   {"age": 4,
                    "event_type": "memory",
                    "tilesets_dir": "game/assets/images/tilesets",
                    "level_path": "game/assets/levels/level_2.json",
                    },
                   {"age": 3, "event_type": "memory", "level_path": "game/assets/levels/level_3.json",
                    "tilesets_dir": "game/assets/images/tilesets"}
                   ]

    },
    {
        "total_age": 45,
        "events": [{
            "age": 44,
            "level_path": "game/assets/levels/level_4.json",
            "event_type": "memory",
            "tilesets_dir": "game/assets/images/tilesets"
        }, {
            "age": 40,
            "level_path": "game/assets/levels/level_5.json",
            "event_type": "memory",
            "tilesets_dir": "game/assets/images/tilesets"
        }]
    },
    {
        "total_age":65,
        "events": [{
            "age":65,
            "level_path": "game/assets/levels/level_6.json",
            "event_type": "memory",
            "tilesets_dir": "game/assets/images/tilesets"

        }]
    }
]


def get_timeline_stuff(level):
    return TIMELINE_CONTS[level]
