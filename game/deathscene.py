import pygame

from core.state_manager import GameState
from core.tilemap_loader import Level
from core.camera import Camera  # adjust path if Camera lives elsewhere


class DeathScene(GameState):
    DEFAULT_LEVEL_PATH = "game/assets/levels/death_1.json"
    DEFAULT_TILESETS_DIR = "game/assets/images/tilesets"

    MIN_DISPLAY_TIME = 1.0  # seconds before any input can skip it -

    # stops an accidental leftover keypress from
    # instantly skipping the scene

    def __init__(self, manager):
        super().__init__(manager)
        self.level = None
        self.camera = None
        self.size = None
        self.next_state = None
        self.time_in_scene = 0.0

    def enter(self, size=(960, 540), next_state=None, level_path=None, tilesets_dir=None, **kwargs):
        #  self.manager.switch(DeathScene(self.manager), size=screen.get_size(), next_state=NextLevelState(self.manager), level_path=..., tilesets_dir=...)
        self.size = size
        self.next_state = next_state
        self.level = Level.load(
            level_path or self.DEFAULT_LEVEL_PATH,
            tilesets_dir=tilesets_dir or self.DEFAULT_TILESETS_DIR,
        )
        self.camera = Camera(size[0], size[1], smoothing=0.1)
        self.time_in_scene = 0.0

    def handle_event(self, event):
        if self.time_in_scene < self.MIN_DISPLAY_TIME:
            return
        if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            self._advance()

    def _advance(self):
        if self.next_state is not None:
            self.manager.switch(self.next_state)
        else:
            self.manager.pop()

    def _camera_rect(self):
        return pygame.Rect(round(self.camera.offset.x), round(self.camera.offset.y), self.size[0], self.size[1])

    def update(self, dt):
        self.time_in_scene += dt

    def draw(self, surface):
        surface.fill((25, 35, 60))
        camera_rect = self._camera_rect()
        self.level.draw(surface, camera_rect)
