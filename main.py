import sys

import pygame
from game.timeline_dat import get_timeline_stuff
from core.audio_manager import AudioManager
from core.display import VirtualDisplay
from core.input_manager import InputManager
from core.state_manager import StateManager
from core.states import MenuState
from game.deathscene import DeathScene
from game.levels import get_level
from game.play import PlayState
from game.timeline import Timeline

# The window starts at this size and can be freely resized (it's created
# with pygame.RESIZABLE). Everything - game and UI - actually draws at
# VIRTUAL_WIDTH x VIRTUAL_HEIGHT; VirtualDisplay scales that image up (or
# down) to fill the window each frame, letterboxed, so nothing needs to
# know the window size or re-layout on resize. See core/display.py.
#
# These match 1:1 by default so existing UI sizing (fonts, button rects,
# etc.) looks the same as before resizing was added. For a lower-res
# pixel-art look - draw small, scale up - drop VIRTUAL_WIDTH/HEIGHT to
# half or a quarter of WINDOW_WIDTH/HEIGHT; VirtualDisplay does the rest.
WINDOW_WIDTH = 960
WINDOW_HEIGHT = 540
VIRTUAL_WIDTH = WINDOW_WIDTH / 3 # 320
VIRTUAL_HEIGHT = WINDOW_HEIGHT / 3 # 180
#320x180

# Example bindings - core/input_manager.py's InputManager takes any
# action-name -> key-list mapping, so replace these with whatever your
# game actually needs.
BINDINGS = {
    "left": [pygame.K_a, pygame.K_LEFT],
    "right": [pygame.K_d, pygame.K_RIGHT],
    "jump": [pygame.K_w, pygame.K_UP],

}


def build_play_state(states, input_manager, audio_manager, level_index=0):
    level = get_level(level_index)
    return PlayState(
        states, input_manager, audio_manager,
        size=(VIRTUAL_WIDTH, VIRTUAL_HEIGHT),
        on_quit_to_menu=lambda: states.reset(build_menu_state(states, input_manager, audio_manager)),
        level_path=level["level_path"],
        tilesets_dir=level["tilesets_dir"],
    )


def build_timeline_state(states, input_manager, audio_manager, level_index=0):
    return Timeline(
        states, timeline_data=get_timeline_stuff(level_index),
        input_manager=input_manager, audio_manager=audio_manager,
        on_quit_to_menu=lambda: states.reset(build_menu_state(states, input_manager, audio_manager)),
    )


def start_level(states, input_manager, audio_manager, level_index=0):
    """Switches to level_index's death scene; the death scene switches to
    the level itself (already built, so it's ready the moment the player
    advances past the death scene) once the player presses a key."""
    level = get_level(level_index)
    timeline_state = build_timeline_state(states, input_manager, audio_manager, level_index)
    states.switch(
        DeathScene(states),
        size=(VIRTUAL_WIDTH, VIRTUAL_HEIGHT),
        next_state=timeline_state,
        level_path=level["death_path"],
        tilesets_dir=level["death_tilesets_dir"],
    )


def build_menu_state(states, input_manager, audio_manager):
    return MenuState(
        states, audio_manager, title="Retrace",
        on_start=lambda: start_level(states, input_manager, audio_manager, 0),
        size=(VIRTUAL_WIDTH, VIRTUAL_HEIGHT),
    )


def main():
    pygame.init()
    display = VirtualDisplay(
        (VIRTUAL_WIDTH, VIRTUAL_HEIGHT),
        window_size=(WINDOW_WIDTH, WINDOW_HEIGHT),
        title="Retrace",
    )
    clock = pygame.time.Clock()

    input_manager = InputManager(BINDINGS)
    audio_manager = AudioManager()

    states = StateManager()
    states.push(build_menu_state(states, input_manager, audio_manager))

    running = True
    while running:
        dt = clock.tick(60) / 1000
        events = pygame.event.get()
        input_manager.update(events)

        for event in events:
            if event.type == pygame.QUIT:
                running = False
            display.handle_event(event)
            states.handle_event(event)

        # Polled every frame (not just on MOUSEMOTION) so hover states stay
        # correct even while the cursor sits still - display.handle_event
        # only rewrites event.pos for events that actually fire.
        input_manager.mouse_pos.update(display.window_to_virtual(pygame.mouse.get_pos()))

        states.update(dt)
        states.draw(display.surface)
        display.present()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
