import math
import random

import pygame
from pygame import gfxdraw

from core.core_funcs import resource_path
from core.particles import ParticleSystem
from core.state_manager import GameState
from core.states import PauseState
from core.tilemap_loader import Level
from core.camera import Camera
from core.ui.pixel_font import PixelFont
from game.levels import MUSIC_FADE_MS, get_level
from game.play import PlayState

TIMELINE_DUST_PRESET = {
    "count": 1,
    "speed": (2, 5),
    "angle": (0, 360),
    "gravity": 0,
    "color": (200, 200, 220, 90),
    "size": (1, 2),
    "lifetime": (6, 10),
}
TIMELINE_PARTICLE_INTERVAL = 1.4
TIMELINE_PARTICLE_PRESPAWN = 5


class Timeline(GameState):
    UNVISITED_COLOR = (255, 255, 255)
    VISITED_COLOR = (110, 200, 160)
    HOVER_COLOR = (255, 70, 70)
    TRACK_GLOW_COLOR = (185, 165, 235)

    def __init__(self, manager, timeline_data, level_index=0, input_manager=None, audio_manager=None,
                 on_quit_to_menu=None):
        super().__init__(manager)
        self.level = None
        self.camera = None
        self.size = None
        self.next_state = None
        self.time_in_scene = 0.0
        self.timeline_data = timeline_data
        self.level_index = level_index
        self.circle_rects = []
        self.visited_events = set()
        self.input_manager = input_manager
        self.audio_manager = audio_manager
        self.on_quit_to_menu = on_quit_to_menu
        self.mouse_pos = (0, 0)
        self.title_font = PixelFont(scale=3)
        self.event_font = PixelFont(scale=1)

        self.particles = ParticleSystem()
        self.particles.register_preset("timeline_dust", TIMELINE_DUST_PRESET)
        self._particle_timer = 0.0
        self._particles_seeded = False

    def _prespawn_particles(self):
        w, h = self.size
        for _ in range(TIMELINE_PARTICLE_PRESPAWN):
            pos = (random.uniform(0, w), random.uniform(0, h))
            before = len(self.particles.particles)
            self.particles.emit("timeline_dust", pos)
            for p in self.particles.particles[before:]:
                p.age = random.uniform(0, p.lifetime)

    def enter(self, size=(960, 540), next_state=None, level_path=None, tilesets_dir=None, **kwargs):

        self.size = size
        self.next_state = next_state
        self.audio_manager.pause_music()

        self.camera = Camera(size[0], size[1], smoothing=0.1)
        self.time_in_scene = 0.0

        if not self._particles_seeded:
            self._prespawn_particles()
            self._particles_seeded = True

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.manager.push(PauseState(
                self.manager, self.audio_manager, on_quit=self.on_quit_to_menu, size=self.size))
            return
        if event.type == pygame.MOUSEBUTTONDOWN:
            for i, circle in enumerate(self.circle_rects):
                if self._point_in_circle(circle, event.pos):
                    self.audio_manager.play("select")
                    self._select_event(self.timeline_data["events"][i])
                    break

    @staticmethod
    def _point_in_circle(circle, pos):
        cx, cy = circle["center"]
        dx, dy = pos[0] - cx, pos[1] - cy
        return dx * dx + dy * dy <= circle["radius"] ** 2

    def _select_event(self, event_data):
        level_path = event_data.get("level_path")
        if level_path is None:
            self._advance()
            return

        tilesets_dir = event_data.get("tilesets_dir", resource_path("game/assets/images/tilesets"))
        self.visited_events.add(level_path)

        music_path = get_level(self.level_index)["music_path"]
        self.audio_manager.play_music(music_path, loops=-1, fade_ms=MUSIC_FADE_MS)

        def back_to_timeline():
            self.manager.pop()
            self.manager.pop(size=self.size)

        self.manager.push(
            PlayState(
                self.manager, self.input_manager, self.audio_manager,
                size=self.size,
                on_quit_to_menu=back_to_timeline,
                quit_label="Back to Timeline",
                level_path=level_path,
                tilesets_dir=tilesets_dir,
                level_index=self.level_index,
            )
        )

    def _advance(self):
        if self.next_state is not None:
            self.manager.switch(self.next_state)
        else:
            self.manager.pop()

    def _camera_rect(self):
        return pygame.Rect(round(self.camera.offset.x), round(self.camera.offset.y), self.size[0], self.size[1])

    def update(self, dt):
        self.time_in_scene += dt

        self._particle_timer += dt
        if self._particle_timer >= TIMELINE_PARTICLE_INTERVAL:
            self._particle_timer -= TIMELINE_PARTICLE_INTERVAL
            w, h = self.size
            self.particles.emit("timeline_dust", (random.uniform(0, w), random.uniform(0, h)))
        self.particles.update(dt)

        mouse_pos = self.input_manager.mouse_pos if self.input_manager is not None else self.mouse_pos
        events = self.timeline_data["events"]
        for i, circle in enumerate(self.circle_rects):
            visited = events[i].get("level_path") in self.visited_events
            base_color = self.VISITED_COLOR if visited else self.UNVISITED_COLOR
            circle["color"] = self.HOVER_COLOR if self._point_in_circle(circle, mouse_pos) else base_color

            circle["visited"] = visited

    @staticmethod
    def _scaled(color, factor):
        return tuple(min(255, round(c * factor)) for c in color)

    def _draw_dot_glow(self, glow_surf, center, color, pulse=0.0):

        cx, cy = int(center[0]), int(center[1])
        base_radii = (16, 10, 6)
        for radius, factor in zip(base_radii, (0.12, 0.22, 0.35)):
            r = radius + int(pulse * 3)
            gfxdraw.filled_circle(glow_surf, cx, cy, r, self._scaled(color, factor))

    def draw(self, surface):
        surface.fill((25, 35, 60))
        camera_rect = self._camera_rect()
        width = (surface.get_width() * 3 / 4) - (surface.get_width() / 4)
        x = surface.get_width() // 4
        track_y = surface.get_height() // 2

        glow_surf = pygame.Surface(surface.get_size())
        glow_surf.fill((0, 0, 0))

        pulse = 0.5 + 0.5 * math.sin(self.time_in_scene * 2.2)

        radius = 5
        o = 0
        for thing in self.timeline_data["events"]:
            center = (x + (width * thing["order"] / max(1, len(self.timeline_data["events"]) - 1)),
                      track_y - radius)
            if len(self.circle_rects) < len(self.timeline_data["events"]):
                self.circle_rects.append({"center": center, "radius": radius, "color": (255, 255, 255),
                                          "visited": False})

            color = self.circle_rects[o]["color"]
            visited = self.circle_rects[o].get("visited", False)

            dot_pulse = pulse if not visited and color == self.UNVISITED_COLOR else 0.0
            self._draw_dot_glow(glow_surf, center, color, pulse=dot_pulse)
            o += 1

        surface.blit(glow_surf, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

        pygame.draw.line(surface, (255, 255, 255), (x, track_y), (x + width, track_y), 2)

        title = self.timeline_data.get("title") or f"Age {self.timeline_data.get('total_age', '')}"
        title_surf = self.title_font.render(title, False, (255, 255, 255))
        surface.blit(title_surf, title_surf.get_rect(midtop=(surface.get_width() // 2, 24)))

        o = 0
        for thing in self.timeline_data["events"]:
            center = self.circle_rects[o]["center"]
            pygame.draw.circle(surface, self.circle_rects[o]["color"], center, radius)

            name = thing.get("name")
            if name:
                name_surf = self.event_font.render(name, False, (220, 220, 230))
                surface.blit(name_surf, name_surf.get_rect(midbottom=(center[0], center[1] - 18)))
            o += 1

        self.particles.draw(surface)