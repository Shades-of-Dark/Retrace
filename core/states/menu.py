import random

import pygame

from ..particles import ParticleSystem
from ..state_manager import GameState
from ..ui import DEFAULT_THEME, Button, Label, PixelFont, UIManager, ui_scale
from .options import OptionsState

MENU_DUST_PRESET = {
    "count": 1,
    "speed": (8, 20),
    "angle": (-95, -85),   # roughly upward: pygame's rotate() is y-down,
                            # so -90 (not 90) is "up" here
    "gravity": -2,          # slight negative gravity keeps them drifting
                            # up instead of arcing back down
    "color": (200, 200, 220, 90),
    "size": (1, 2),
    "lifetime": (4, 7),
}
MENU_DUST_SPAWN_INTERVAL = 0.15
MENU_DUST_PRESPAWN_COUNT = 24


def _post_quit():
    pygame.event.post(pygame.event.Event(pygame.QUIT))


def _surface_size():
    surface = pygame.display.get_surface()
    return surface.get_size() if surface else (960, 540)


class MenuState(GameState):
    """Title screen: Start / Options / Quit. Generic - the game layer
    supplies on_start (typically manager.switch(build_play_state()));
    Options and its audio wiring are handled entirely within core.
    on_quit defaults to posting a QUIT event, which main.py's event loop
    already handles."""

    def __init__(self, manager, audio_manager, title="Game Title",
                 on_start=None, on_quit=None, theme=None, size=None):
        super().__init__(manager)
        self.audio = audio_manager
        self.title = title
        self.on_start = on_start
        self.on_quit = on_quit or _post_quit
        self.theme = theme or DEFAULT_THEME
        self.size = size
        scale = ui_scale((self.size or _surface_size())[0])
        self.title_font = PixelFont(scale=max(1, round(4 * scale)))
        self.ui = UIManager()
        self._build_ui(scale)

        self.particles = ParticleSystem()
        self.particles.register_preset("menu_dust", MENU_DUST_PRESET)
        self._dust_timer = 0.0
        self._prespawn_dust(*(self.size or _surface_size()))

    def _prespawn_dust(self, width, height):
        # Spawn a batch already mid-flight at random y-positions instead of
        # everything starting at the bottom edge and taking several
        # seconds to drift up and fill the screen.
        for _ in range(MENU_DUST_PRESPAWN_COUNT):
            pos = (random.uniform(0, width), random.uniform(0, height))
            before = len(self.particles.particles)
            self.particles.emit("menu_dust", pos)
            for p in self.particles.particles[before:]:
                p.age = random.uniform(0, p.lifetime)

    def _build_ui(self, scale):
        width, height = self.size or _surface_size()
        center_x = width // 2
        button_width, button_height, gap = round(220 * scale), round(44 * scale), round(16 * scale)
        start_y = height // 2 - round(10 * scale)
        font = PixelFont(scale=max(1, round(2 * scale)))

        self.ui.add(Button(
            (center_x - button_width // 2, start_y, button_width, button_height),
            "Start", on_click=self._click(self._start), theme=self.theme, font=font))
        self.ui.add(Button(
            (center_x - button_width // 2, start_y + (button_height + gap), button_width, button_height),
            "Options", on_click=self._click(self._open_options), theme=self.theme, font=font))
        self.ui.add(Button(
            (center_x - button_width // 2, start_y + 2 * (button_height + gap), button_width, button_height),
            "Quit", on_click=self._click(self.on_quit), theme=self.theme, font=font))

    def _click(self, callback):
        def handler():
            self.audio.play("select")
            if callback:
                callback()
        return handler

    def _start(self):
        if self.on_start:
            self.on_start()

    def _open_options(self):
        self.manager.push(OptionsState(self.manager, self.audio, theme=self.theme, size=self.size))

    def handle_event(self, event):
        self.ui.handle_event(event)

    def update(self, dt):
        self.ui.update(dt)

        width, height = self.size or _surface_size()
        self._dust_timer += dt
        if self._dust_timer >= MENU_DUST_SPAWN_INTERVAL:
            self._dust_timer -= MENU_DUST_SPAWN_INTERVAL
            self.particles.emit("menu_dust", (random.uniform(0, width), height + 4))
        self.particles.update(dt)

    def draw(self, surface):
        surface.fill(self.theme["bg"])
        self.particles.draw(surface)
        title_surf = self.title_font.render(self.title, True, self.theme["text"])
        surface.blit(title_surf, title_surf.get_rect(
            center=(surface.get_width() // 2, surface.get_height() // 3)))
        self.ui.draw(surface)
