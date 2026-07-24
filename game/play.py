import pygame

from core.core_funcs import get_image, palette_swap
from game.grass import Grass, load_grass_frames, sway_phase_delta
from game.water import find_water_bodies, create_water
from game.wind import WindField
from game.tree import Tree
from core.state_manager import GameState
from core.states import PauseState
from core.tilemap_loader import Level
from game.player import Player

from core.camera import Camera

GRASS_LAYER = 2


class PlayState(GameState):
    """Starting point for the game's actual gameplay - fill in
    handle_event/update/draw as you build it out. on_quit_to_menu is
    called by the pause screen's "Quit to menu" button; main.py supplies
    it so this file doesn't need to know how the menu gets built."""

    def __init__(self, manager, input_manager, audio_manager, size, on_quit_to_menu,
                 level_path="game/assets/levels/level_1.json",
                 tilesets_dir="game/assets/images/tilesets",
                 quit_label="Quit to menu"):
        super().__init__(manager)
        self.ramps = None
        self.input = input_manager
        self.audio = audio_manager
        self.size = size
        self.on_quit_to_menu = on_quit_to_menu
        self.quit_label = quit_label

        self.level = Level.load(level_path, tilesets_dir=tilesets_dir)
        spawn = self.level.get_spawn_point(default=(300, 100))
        self.player = Player((spawn.x, spawn.y), (16, 16))

        self.camera = Camera(size[0], size[1], smoothing=0.2)
        self.camera.follow(self.player)
        leaf_sheet = pygame.image.load("game/assets/images/particles/leaves.png").convert()
        leaves_img = []
        for i in range(3):
            img = get_image(leaf_sheet, i, 8, 8, color=(0, 0, 0))
            midtone = palette_swap(img, (179, 165, 85), (119, 116, 59))
            darkest = palette_swap(img, (179, 165, 85), (77, 69, 57))
            leaves_img.append(img)
            leaves_img.append(midtone)
            leaves_img.append(darkest)
        self.trees = []
        tree_img = pygame.image.load("game/assets/images/tilesets/tree.png").convert()
        tree_img.set_colorkey((0, 0, 0))
        tree_mask = pygame.image.load("game/assets/images/masks/tree_mask.png").convert()
        tree_mask.set_colorkey((255, 255, 255))
        grass_frames = load_grass_frames("game/assets/images/tilesets")
        targets = pygame.image.load("game/assets/images/tilesets/tree_target.png").convert()
        for bucket in self.level.tilemap.chunks.values():
            for raw in bucket:
                if raw.get("tileset") != "tree":
                    continue

                self.trees.append(Tree(tree_mask, tree_img,
                                       (raw["pos"][0] * self.level.tile_size, raw["pos"][1] * self.level.tile_size),
                                       targets, leaves_img))

        self.grass_by_tile = {}
        for entry in self.level.tilemap.iter_all_tiles(layer=GRASS_LAYER, include_hidden=True):
            self.grass_by_tile[entry.pos] = Grass.spawn_for_tile(entry.rect, grass_frames)

        self.water_tiles = find_water_bodies(self.level.tilemap)

        self.water_bodies = create_water(self.water_tiles, self.level.tile_size)

        self._active_grass_tiles = set()
        self.sway_phase = 0

        self.wind = WindField(tile_size=self.level.tile_size)
        self.level.tilemap.remove_from_draw("tree")
        self.bg_far = pygame.image.load("game/assets/images/parallax_far.png").convert_alpha()
        self.bg_mid = pygame.image.load("game/assets/images/parallax_mid.png").convert_alpha()
        self.bg_near = pygame.image.load("game/assets/images/parallax_near.png").convert_alpha()

    def _camera_rect(self):
        return pygame.Rect(round(self.camera.offset.x), round(self.camera.offset.y), self.size[0], self.size[1])

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.manager.push(PauseState(
                self.manager, self.audio, on_quit=self.on_quit_to_menu,
                quit_label=self.quit_label, size=self.size))

    def update(self, dt):

        camera_rect = self._camera_rect()
        move_x = self.input.get_axis("left", "right")
        jump_pressed = self.input.is_action_pressed("jump")
        solids = self.level.get_solid_rects(camera_rect)
        self.ramps = self.level.get_ramps(camera_rect)

        self.player.physics_update(dt, self.level.tile_size, move_x, jump_pressed, solids, self.ramps)
        self.camera.update(dt)

        tile = self.level.tile_size
        player_tile = (int(self.player.rect.centerx // tile), int((self.player.rect.bottom - 1) // tile))
        near_tiles = {(player_tile[0] + dx, player_tile[1]) for dx in (-1, 0, 1)}

        still_active = set()
        for key in near_tiles | self._active_grass_tiles:
            blades = self.grass_by_tile.get(key)
            if not blades:
                continue
            for blade in blades:
                blade.bend_towards(self.player, dt)
            if not all(blade.settled for blade in blades):
                still_active.add(key)
        self._active_grass_tiles = still_active

        self.wind.update(dt, camera_rect)
        # After wind.update() so this frame's just-refreshed smoothed gust
        # speed is what speeds the sway up, not last frame's.
        self.sway_phase += sway_phase_delta(dt, self.wind.smoothed_screen_speed)

        # A pond nowhere near the camera can't have the player in it
        # (camera.follow keeps the player roughly centered) and nobody's
        # looking at its ripple anyway - skip its physics entirely rather
        # than stepping every surface point of every pond in the level
        # every frame regardless of visibility. It just resumes exactly
        # where it left off once back on screen (dt isn't owed anywhere,
        # a skipped frame simply isn't simulated).
        for body in self.water_bodies:
            if body.bounds.colliderect(camera_rect):
                body.check_splash(self.player)
                body.apply_buoyancy(self.player, dt)
                body.update(dt)

        for tree in self.trees:
            tree.update(dt, wind=self.wind, camera_rect=self._camera_rect())

    def draw(self, surface):
        surface.fill(pygame.Color("#d2c9a5"))
        cam_x = self.camera.offset.x
        for img, speed in ((self.bg_far, 0.2), (self.bg_mid, 0.4), (self.bg_near, 0.6)):
            offset_x = int(-cam_x * speed) % img.get_width()
            surface.blit(img, (offset_x - img.get_width(), 0))
            surface.blit(img, (offset_x, 0))
        camera_rect = self._camera_rect()
        self.level.draw(surface, camera_rect, exclude_layers={GRASS_LAYER})
        for tree in self.trees:
            tree.draw(surface, self.camera)

        gust_speed = self.wind.smoothed_screen_speed
        tile = self.level.tile_size

        self.player.draw(surface, self.camera)
        for (tx, ty), blades in self.grass_by_tile.items():
            tile_rect = pygame.Rect(tx * tile - tile, ty * tile - tile, tile * 3, tile * 3)
            if not tile_rect.colliderect(camera_rect):
                continue
            for blade in blades:
                blade.draw(surface, self.camera, self.sway_phase, gust_speed)
        for body in self.water_bodies:
            if body.bounds.colliderect(camera_rect):
                body.draw(surface, self.camera)
