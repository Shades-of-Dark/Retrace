from core.core_funcs import resource_path

TIMELINE_CONTS = [
    {
        "total_age": 9,
        "title": "Timeline",
        "events": [
            {"age": 9, "order": 0, "event_type": "memory", "name": "Front Yard",
             "level_path": resource_path("game/assets/levels/level_1.json"),
             "tilesets_dir": resource_path("game/assets/images/tilesets")},
            {"age": 9, "order": 1, "event_type": "memory", "name": "Kitchen",
             "level_path": resource_path("game/assets/levels/level_3.json"),
             "tilesets_dir": resource_path("game/assets/images/tilesets")},
            {"age": 9, "order": 2, "event_type": "memory", "name": "Bedroom",
             "level_path": resource_path("game/assets/levels/level_2.json"),
             "tilesets_dir": resource_path("game/assets/images/tilesets")},
        ]
    },
    {
        "total_age": 29,
        "title": "Timeline",
        "events": [
            {"age": 29, "order": 0, "event_type": "memory", "name": "Office",
             "level_path": resource_path("game/assets/levels/level_4.json"),
             "tilesets_dir": resource_path("game/assets/images/tilesets")},
            {"age": 29, "order": 1, "event_type": "memory", "name": "Apartment",
             "level_path": resource_path("game/assets/levels/level_5.json"),
             "tilesets_dir": resource_path("game/assets/images/tilesets")},
        ]
    },
    {
        "total_age": 71,
        "title": "Timeline",
        "events": [
            {"age": 71, "order": 0, "event_type": "memory", "name": "Living Room",
             "level_path": resource_path("game/assets/levels/level_6.json"),
             "tilesets_dir": resource_path("game/assets/images/tilesets")},
            {"age": 71, "order": 1, "event_type": "memory", "name": "Bedroom",
             "level_path": resource_path("game/assets/levels/level_7.json"),
             "tilesets_dir": resource_path("game/assets/images/tilesets")},
        ]
    }
]


def get_timeline_stuff(level):
    return TIMELINE_CONTS[level]
