import pygame

from core.state_manager import GameState
from core.states import PauseState
from core.tilemap_loader import Level
from game.player import Player

from core.camera import Camera


class PlayState(GameState):
    """Starting point for the game's actual gameplay - fill in
    handle_event/update/draw as you build it out. on_quit_to_menu is
    called by the pause screen's "Quit to menu" button; main.py supplies
    it so this file doesn't need to know how the menu gets built."""

    def __init__(self, manager, input_manager, audio_manager, size, on_quit_to_menu,
                 level_path="game/assets/levels/level_1.json",
                 tilesets_dir="game/assets/images/tilesets"):
        super().__init__(manager)
        self.ramps = None
        self.input = input_manager
        self.audio = audio_manager
        self.size = size
        self.on_quit_to_menu = on_quit_to_menu

        self.level = Level.load(level_path, tilesets_dir=tilesets_dir)
        spawn = self.level.get_spawn_point(default=(300, 100))
        self.player = Player((spawn.x, spawn.y), (16, 16))

        self.camera = Camera(size[0], size[1], smoothing=0.2)
        self.camera.follow(self.player)

    def _camera_rect(self):
        return pygame.Rect(round(self.camera.offset.x), round(self.camera.offset.y), self.size[0], self.size[1])

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.manager.push(PauseState(
                self.manager, self.audio, on_quit=self.on_quit_to_menu, size=self.size))

    def update(self, dt):

        camera_rect = self._camera_rect()
        move_x = self.input.get_axis("left", "right")
        jump_pressed = self.input.is_action_pressed("jump")
        solids = self.level.get_solid_rects(camera_rect)
        self.ramps = self.level.get_ramps(camera_rect)

        self.player.physics_update(dt, self.level.tile_size,move_x, jump_pressed,solids, self.ramps )
        self.camera.update(dt)

    def draw(self, surface):
        surface.fill((24, 26, 34))

        camera_rect = self._camera_rect()
        self.level.draw(surface, camera_rect)
        self.player.draw(surface, self.camera)
