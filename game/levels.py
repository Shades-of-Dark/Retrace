
from core.states import MenuState
from game.deathscene import DeathScene
from game.timeline_dat import get_timeline_stuff

LEVELS = [
    {
        "death_path": "game/assets/levels/death_1.json",
        "tilesets_dir": "game/assets/images/tilesets",
    },
    {
        "death_path": "game/assets/levels/death_2.json",
        "tilesets_dir": "game/assets/images/tilesets",
    },
    {
        "death_path": "game/assets/levels/death_3.json",
        "tilesets_dir": "game/assets/images/tilesets",
    }

]


def get_level(index):

    return LEVELS[index]


def build_timeline_state(states, input_manager, audio_manager, size, level_index=0):

    from game.timeline import Timeline

    return Timeline(
        states, timeline_data=get_timeline_stuff(level_index), level_index=level_index,
        input_manager=input_manager, audio_manager=audio_manager,
        on_quit_to_menu=lambda: states.reset(build_menu_state(states, input_manager, audio_manager, size)),
    )


def start_level(states, input_manager, audio_manager, size, level_index=0):

    level = get_level(level_index)
    timeline_state = build_timeline_state(states, input_manager, audio_manager, size, level_index)
    states.switch(
        DeathScene(states),
        size=size,
        next_state=timeline_state,
        level_path=level["death_path"],
        tilesets_dir=level["tilesets_dir"],
        level_index=level_index,
    )


def build_menu_state(states, input_manager, audio_manager, size):
    return MenuState(
        states, audio_manager, title="Retrace",
        on_start=lambda: start_level(states, input_manager, audio_manager, size, 0),
        size=size,
    )
