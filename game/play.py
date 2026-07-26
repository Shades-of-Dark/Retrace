import math

import pygame

from core.core_funcs import additive_glow, desaturate_surface, get_image, palette_swap, resource_path
from core.particles import ParticleSystem
from game.grass import Grass, load_grass_frames, sway_phase_delta
from game.item import Item
from game.levels import build_menu_state, start_level
from game.reaper_scene import ReaperScene
from game.timeline_dat import TIMELINE_CONTS
from game.timeline_transition import TimelineTransition
from game.water import find_water_bodies, create_water
from game.wind import WindField
from game.tree import Tree
from core.state_manager import GameState
from core.states import PauseState
from core.tilemap_loader import Level
from core.ui.pixel_font import PixelFont
from game.player import Player

from core.camera import Camera

GRASS_LAYER = 2
GRASS_TILESET = "decor_0"
MESSAGE_OFFSET_Y = 16
PROMPT_OFFSET_Y = 28
ITEM_TEXT_SCALE = 1
ITEM_TEXT_LINE_GAP = 2
ITEM_TEXT_MARGIN = 12
DESATURATION_BY_LEVEL = [0.0, 0.3, 0.55]
HAIR_COLOR_BY_LEVEL = [
    (75, 61, 68),  # Run 1 - original
    (75, 61, 68),  # same hair
    (210, 208, 200),  # Run 3 - white/gray
]
TUTORIAL_LEVEL_INDEX = 0
TUTORIAL_TEXT = "Find what killed you. Change it."
TUTORIAL_OFFSET_Y = 24
WRONG_SHAKE_INTENSITY = 2.5
WRONG_SHAKE_DURATION = 0.15
WRONG_SHAKE_COOLDOWN = 0.25
FOUND_FREEZE_DURATION = 0.2
FOUND_GLOW_RAMP = 0.2
FOUND_GLOW_COLOR = (255, 210, 90)
FOUND_GLOW_MAX_AMOUNT = 0.4

FOUND_PULSE_PERIOD = 0.7
FOUND_PULSE_MAX_RADIUS = 22
FOUND_PULSE_COLOR = (255, 235, 160)
FOUND_PULSE_HALO_COLOR = (20, 15, 10)
CORRECT_PICKUP_PRESET = {
    "count": (12, 18),
    "speed": (30, 70),
    "angle": (0, 360),
    "gravity": 60,
    "color": (255, 215, 130, 220),
    "size": (1, 3),
    "lifetime": (0.4, 0.8),
}


class PlayState(GameState):
    MIN_FOUND_DISPLAY_TIME = 1.0

    def __init__(self, manager, input_manager, audio_manager, size, on_quit_to_menu,
                 level_path=resource_path("game/assets/levels/level_1.json"),
                 tilesets_dir=resource_path("game/assets/images/tilesets"),
                 quit_label="Quit to menu",
                 level_index=0):
        super().__init__(manager)
        self.ramps = None
        self.input = input_manager
        self.audio = audio_manager
        self.size = size
        self.on_quit_to_menu = on_quit_to_menu
        self.quit_label = quit_label
        self.active_message = None

        self.active_item = None
        self.shake_cooldown = 0.0
        self.particles = ParticleSystem()
        self.particles.register_preset("correct_pickup", CORRECT_PICKUP_PRESET)

        self.state = "playing"
        self.found_item = None
        self.found_timer = 0.0
        self.found_message_shown = False

        self.level_index = level_index

        self.level = Level.load(level_path, tilesets_dir=tilesets_dir)
        spawn = self.level.get_spawn_point(default=(300, 100))
        hair_color = HAIR_COLOR_BY_LEVEL[min(level_index, len(HAIR_COLOR_BY_LEVEL) - 1)]
        self.player = Player((spawn.x, spawn.y), (16, 16), hair_color=hair_color, audio_manager=audio_manager)

        self.tutorial_text = (
            TUTORIAL_TEXT if level_index == TUTORIAL_LEVEL_INDEX else None
        )
        self.tutorial_pos = (spawn.x + 30, spawn.y - TUTORIAL_OFFSET_Y)

        self.camera = Camera(size[0], size[1], smoothing=0.2, intro_smoothing=0.04)
        self.camera.follow(self.player)
        leaf_sheet = pygame.image.load(resource_path("game/assets/images/particles/leaves.png")).convert()
        leaves_img = []
        for i in range(3):
            img = get_image(leaf_sheet, i, 8, 8, color=(0, 0, 0))
            midtone = palette_swap(img, (179, 165, 85), (119, 116, 59))
            darkest = palette_swap(img, (179, 165, 85), (77, 69, 57))
            leaves_img.append(img)
            leaves_img.append(midtone)
            leaves_img.append(darkest)
        self.trees = []
        tree_img = pygame.image.load(resource_path("game/assets/images/tilesets/tree.png")).convert()
        tree_img.set_colorkey((0, 0, 0))
        tree_mask = pygame.image.load(resource_path("game/assets/images/masks/tree_mask.png")).convert()
        tree_mask.set_colorkey((255, 255, 255))
        grass_frames = load_grass_frames(resource_path("game/assets/images/tilesets"))
        targets = pygame.image.load(resource_path("game/assets/images/tilesets/tree_target.png")).convert()
        for bucket in self.level.tilemap.chunks.values():
            for raw in bucket:
                if raw.get("tileset") != "tree":
                    continue

                self.trees.append(Tree(tree_mask, tree_img,
                                       (raw["pos"][0] * self.level.tile_size, raw["pos"][1] * self.level.tile_size),
                                       targets, leaves_img))

        self.grass_by_tile = {}
        for entry in self.level.tilemap.iter_all_tiles(layer=GRASS_LAYER, include_hidden=True):

            if entry.tileset != GRASS_TILESET:
                continue
            self.grass_by_tile[entry.pos] = Grass.spawn_for_tile(entry.rect, grass_frames)

        self.water_tiles = find_water_bodies(self.level.tilemap)

        self.water_bodies = create_water(self.water_tiles, self.level.tile_size)

        self._active_grass_tiles = set()
        self.sway_phase = 0

        self.wind = WindField(tile_size=self.level.tile_size)
        self.level.tilemap.remove_from_draw("tree")
        self.level.tilemap.remove_from_draw(GRASS_TILESET)
        self.bg_far = pygame.image.load(resource_path("game/assets/images/backgrounds/parallax_far.png")).convert_alpha()
        self.bg_mid = pygame.image.load(resource_path("game/assets/images/backgrounds/parallax_mid.png")).convert_alpha()
        self.bg_near = pygame.image.load(resource_path("game/assets/images/backgrounds/parallax_near.png")).convert_alpha()
        self.items = []

        self._spawn_role_item("bike", "The front wheel is loose.", is_correct=True)
        self._spawn_role_item("ball", "I remember chasing this ball past the curb before, nothing happened that time.")
        self._spawn_role_item("note",
                              "Not my handwriting. Theirs. A dare to race past the corner.")
        self._spawn_role_item("mom", "Later, she said, still on the phone. She always said later.")
        self._spawn_role_item("pill", "Four of these since noon. I told myself it was just today.", is_correct=True)
        self._spawn_role_item("deadline", "Almost done. Just needed one more night.")
        self._spawn_role_item("phone", "Missed calls. I meant to call back. I always meant to.")
        self._spawn_role_item("calendar", "No one's written on this in months. Neither have I.")
        self._spawn_role_item("disc_phone", "Never got it reconnected. There was no one urgent enough to call.",
                              is_correct=True)
        self._spawn_role_item("picture", "Them, and me. I forgot I still had this. I never called.")
        for exit_entity in self.level.tilemap.get_entities("level_exit"):
            exit_image = pygame.Surface((self.level.tile_size, self.level.tile_size), pygame.SRCALPHA)
            exit_item = Item(
                image=exit_image,
                pos=exit_entity["pos"],
                message="",
                on_interact=self.on_exit_interact,
            )
            self.items.append(exit_item)

    def _spawn_role_item(self, role, message, is_correct=False):

        entry = self.level.get_marker_entry("role", role)
        if entry is None:
            return None
        self.level.tilemap.remove_from_draw_by_prop("role", role)
        item = Item(
            image=entry.get_surface(),
            pos=entry.rect.topleft,
            message=message,
            is_correct=is_correct,
            on_interact=self.on_item_interact,
        )
        self.items.append(item)
        return item

    def _camera_rect(self):
        total = self.camera.total_offset
        return pygame.Rect(round(total.x), round(total.y), self.size[0], self.size[1])

    def _physics_rect(self):
        # Collision must never depend on where the camera currently is (it
        # can lag well behind the player during the intro pan) - query
        # solids/ramps in a same-sized window centered on the player instead.
        w, h = self.size
        return pygame.Rect(0, 0, w, h).move(
            round(self.player.rect.centerx - w / 2),
            round(self.player.rect.centery - h / 2),
        )

    def on_item_interact(self, item):
        self.audio.play("interact")
        if item.is_correct:
            self.on_correct_clue_found(item)
        else:
            self.on_wrong_clue_found(item)

    def on_exit_interact(self, item):
        self.audio.play("interact")
        self.manager.pop(size=self.size)

    def on_correct_clue_found(self, item):
        self.found_item = item
        self.found_timer = 0.0
        self.found_message_shown = False
        self.audio.play("correct_clue")
        self.particles.emit("correct_pickup", item.rect.center)

        self.state = "found"

    def on_wrong_clue_found(self, item):
        self.active_item = item
        item.mark_checked_wrong()
        self.audio.play("wrong_clue")
        if self.shake_cooldown <= 0.0:
            self.camera.shake(WRONG_SHAKE_INTENSITY, WRONG_SHAKE_DURATION, randomness=0.6)
            self.shake_cooldown = WRONG_SHAKE_COOLDOWN
        self.show_message(item.message)

    def show_message(self, text):
        self.active_message = text

    def _get_transition_data(self):
        prev_age = TIMELINE_CONTS[self.level_index]["total_age"]
        new_age = TIMELINE_CONTS[self.level_index + 1]["total_age"]
        label = f"{new_age - prev_age} years later..."
        return prev_age, new_age, label

    def _advance_to_next_run(self):

        self.audio.stop_music()

        if self.level_index + 1 >= len(TIMELINE_CONTS):
            self._advance_to_reaper_scene()
            return

        prev_age, new_age, label = self._get_transition_data()
        self.manager.switch(
            TimelineTransition(
                self.manager,
                prev_age=prev_age,
                new_age=new_age,
                max_lifespan=90,
                event_label=label,
                size=self.size,
                on_complete=lambda: start_level(
                    self.manager, self.input, self.audio, self.size, self.level_index + 1
                ),
            )
        )

    def _advance_to_reaper_scene(self):
        self.audio.play("reaching_reaper")
        self.manager.switch(
            ReaperScene(
                self.manager,
                self.size,
                on_complete=lambda: self.manager.reset(
                    build_menu_state(self.manager, self.input, self.audio, self.size)
                ),
            )
        )

    def handle_event(self, event):
        if self.state == "found":
            if (self.found_timer >= self.MIN_FOUND_DISPLAY_TIME
                    and event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN)):
                self._advance_to_next_run()
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.manager.push(PauseState(
                self.manager, self.audio, on_quit=self.on_quit_to_menu,
                quit_label=self.quit_label, size=self.size))
        for item in self.items:
            item.handle_event(event)

    def update(self, dt):
        if self.shake_cooldown > 0.0:
            self.shake_cooldown -= dt
        self.particles.update(dt)

        if self.state == "found":
            self.found_timer += dt
            if not self.found_message_shown and self.found_timer >= FOUND_FREEZE_DURATION:
                self.found_message_shown = True
                self.show_message(self.found_item.message)
            return

        camera_rect = self._camera_rect()
        physics_rect = self._physics_rect()
        move_x = self.input.get_axis("left", "right")
        jump_pressed = self.input.is_action_pressed("jump")
        solids = self.level.get_solid_rects(physics_rect)
        self.ramps = self.level.get_ramps(physics_rect)

        self.player.physics_update(dt, self.level.tile_size, move_x, jump_pressed, solids, self.ramps)
        self.camera.update(dt)

        for item in self.items:
            item.update(dt, player_rect=self.player.rect)

        if self.active_item is not None and not self.active_item.in_range:
            self.active_message = None
            self.active_item = None

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

        self.sway_phase += sway_phase_delta(dt, self.wind.smoothed_screen_speed)

        for body in self.water_bodies:
            if body.bounds.colliderect(camera_rect):
                body.check_splash(self.player)
                body.apply_buoyancy(self.player, dt)
                body.update(dt)

        for tree in self.trees:
            tree.update(dt, wind=self.wind, camera_rect=self._camera_rect())

    def draw(self, surface):
        surface.fill(pygame.Color("#d2c9a5"))
        cam_x = self.camera.total_offset.x
        for img, speed in ((self.bg_far, 0.2), (self.bg_mid, 0.4), (self.bg_near, 0.6)):
            offset_x = int(-cam_x * speed) % img.get_width()
            surface.blit(img, (offset_x - img.get_width(), 0))
            surface.blit(img, (offset_x, 0))
        camera_rect = self._camera_rect()
        self.level.draw(surface, camera_rect)
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

        amount = DESATURATION_BY_LEVEL[min(self.level_index, len(DESATURATION_BY_LEVEL) - 1)]
        if amount > 0:
            surface.blit(desaturate_surface(surface, amount), (0, 0))

        for item in self.items:
            item.draw(surface, self.camera)
        if self.state == "found" and self.found_item is not None:
            self._draw_found_glow(surface)
        self.particles.draw(surface, self.camera)
        if self.tutorial_text:
            self._draw_tutorial_text(surface)
        if self.active_message:
            self._draw_message(surface)
        if self.state == "found" and self.found_timer >= self.MIN_FOUND_DISPLAY_TIME:
            self._draw_found_prompt(surface)

    @staticmethod
    def _wrap_text(font, text, max_width):
        words = text.split(" ")
        lines = []
        current = ""
        for word in words:
            candidate = f"{current} {word}" if current else word
            if not current or font.size(candidate)[0] <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    def _draw_wrapped_text(self, surface, text, bottom_y, color=(255, 255, 255), alpha=None):
        font = PixelFont(scale=ITEM_TEXT_SCALE)
        max_width = surface.get_width() - ITEM_TEXT_MARGIN * 2
        lines = self._wrap_text(font, text, max_width)
        line_height = font.get_height() + ITEM_TEXT_LINE_GAP
        top = bottom_y - line_height * len(lines)
        for i, line in enumerate(lines):
            line_surf = font.render(line, False, color)
            if alpha is not None:
                line_surf.set_alpha(alpha)
            rect = line_surf.get_rect(midtop=(surface.get_width() // 2, top + i * line_height))
            surface.blit(line_surf, rect)

    def _draw_message(self, surface):
        self._draw_wrapped_text(surface, self.active_message, surface.get_height() - MESSAGE_OFFSET_Y)

    def _draw_found_glow(self, surface):
        item = self.found_item
        rect = self.camera.apply(item.rect)

        ramp_t = min(1.0, self.found_timer / FOUND_GLOW_RAMP)
        glowed = additive_glow(item.get_alpha_image(), FOUND_GLOW_COLOR, FOUND_GLOW_MAX_AMOUNT * ramp_t)
        surface.blit(glowed, rect)

        pulse_t = (self.found_timer % FOUND_PULSE_PERIOD) / FOUND_PULSE_PERIOD
        radius = round(4 + FOUND_PULSE_MAX_RADIUS * pulse_t)
        alpha = round(170 * (1 - pulse_t))
        if alpha > 0:
            glow_surf = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
            center = (radius + 2, radius + 2)

            pygame.draw.circle(glow_surf, (*FOUND_PULSE_HALO_COLOR, round(alpha * 0.5)), center, radius, width=4)
            surface.blit(glow_surf, glow_surf.get_rect(center=rect.center))
            glow_surf.fill((0, 0, 0, 0))
            pygame.draw.circle(glow_surf, (*FOUND_PULSE_COLOR, alpha), center, radius, width=2)
            surface.blit(glow_surf, glow_surf.get_rect(center=rect.center), special_flags=pygame.BLEND_RGBA_ADD)

    def _draw_tutorial_text(self, surface):
        font = PixelFont(scale=ITEM_TEXT_SCALE)
        max_width = 220
        lines = self._wrap_text(font, self.tutorial_text, max_width)
        line_height = font.get_height() + ITEM_TEXT_LINE_GAP
        screen_pos = self.camera.apply_pos(self.tutorial_pos)
        top = screen_pos.y - line_height * len(lines)
        for i, line in enumerate(lines):
            line_surf = font.render(line, False, (255, 255, 255))
            rect = line_surf.get_rect(midtop=(screen_pos.x, top + i * line_height))
            surface.blit(line_surf, rect)

    def _draw_found_prompt(self, surface):
        alpha = int(140 + 100 * math.sin(self.found_timer * 3))
        self._draw_wrapped_text(surface, "You found the fix! Press any key to move on...", surface.get_height() / 4,
                                alpha=alpha)
