import pygame

from core.state_manager import GameState
from core.states import PauseState


class PlayState(GameState):
    """Starting point for the game's actual gameplay - fill in
    handle_event/update/draw as you build it out. on_quit_to_menu is
    called by the pause screen's "Quit to menu" button; main.py supplies
    it so this file doesn't need to know how the menu gets built."""

    def __init__(self, manager, input_manager, audio_manager, size, on_quit_to_menu):
        super().__init__(manager)
        self.input = input_manager
        self.audio = audio_manager
        self.size = size
        self.on_quit_to_menu = on_quit_to_menu

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.manager.push(PauseState(
                self.manager, self.audio, on_quit=self.on_quit_to_menu, size=self.size))

    def update(self, dt):
        pass

    def draw(self, surface):
        surface.fill((24, 26, 34))
