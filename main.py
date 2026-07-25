import sys

import pygame
from core.audio_manager import AudioManager
from core.display import VirtualDisplay
from core.input_manager import InputManager
from core.state_manager import StateManager
from game.levels import build_menu_state


WINDOW_WIDTH = 960
WINDOW_HEIGHT = 540
VIRTUAL_WIDTH = WINDOW_WIDTH / 3 # 320
VIRTUAL_HEIGHT = WINDOW_HEIGHT / 3 # 180
#320x180


BINDINGS = {
    "left": [pygame.K_a, pygame.K_LEFT],
    "right": [pygame.K_d, pygame.K_RIGHT],
    "jump": [pygame.K_w, pygame.K_UP],

}


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
    states.push(build_menu_state(states, input_manager, audio_manager, (VIRTUAL_WIDTH, VIRTUAL_HEIGHT)))

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


        input_manager.mouse_pos.update(display.window_to_virtual(pygame.mouse.get_pos()))

        states.update(dt)
        states.draw(display.surface)
        display.present()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
