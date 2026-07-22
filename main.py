import sys

import pygame

from core.audio_manager import AudioManager
from core.display import VirtualDisplay
from core.input_manager import InputManager
from core.state_manager import StateManager
from core.states import MenuState
from game.play import PlayState

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
VIRTUAL_WIDTH = WINDOW_WIDTH
VIRTUAL_HEIGHT = WINDOW_HEIGHT

# Example bindings - core/input_manager.py's InputManager takes any
# action-name -> key-list mapping, so replace these with whatever your
# game actually needs.
BINDINGS = {
    "left": [pygame.K_a, pygame.K_LEFT],
    "right": [pygame.K_d, pygame.K_RIGHT],
    "up": [pygame.K_w, pygame.K_UP],
    "down": [pygame.K_s, pygame.K_DOWN],
}


def build_play_state(states, input_manager, audio_manager):
    return PlayState(
        states, input_manager, audio_manager,
        size=(VIRTUAL_WIDTH, VIRTUAL_HEIGHT),
        on_quit_to_menu=lambda: states.reset(build_menu_state(states, input_manager, audio_manager)),
    )


def build_menu_state(states, input_manager, audio_manager):
    return MenuState(
        states, audio_manager, title="Gamejam Template",
        on_start=lambda: states.switch(build_play_state(states, input_manager, audio_manager)),
        size=(VIRTUAL_WIDTH, VIRTUAL_HEIGHT),
    )


def main():
    pygame.init()
    display = VirtualDisplay(
        (VIRTUAL_WIDTH, VIRTUAL_HEIGHT),
        window_size=(WINDOW_WIDTH, WINDOW_HEIGHT),
        title="gamejam-template",
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

        states.update(dt)
        states.draw(display.surface)
        display.present()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
