import pygame
from pygame import gfxdraw

from core.state_manager import GameState
from core.ui.pixel_font import PixelFont


class TimelineTransition(GameState):
    LINE_COLOR = (255, 210, 90)
    TRACK_GLOW_COLOR = (185, 165, 235)
    TEXT_COLOR = (245, 235, 210)
    BG_COLOR = (20, 22, 35)

    GROW_DURATION = 1.4
    HOLD_DURATION = 1.0

    def __init__(self, manager, prev_age, new_age, max_lifespan, event_label="",
                 on_complete=None, size=(960, 540), font=None):
        super().__init__(manager)
        self.prev_age = prev_age
        self.new_age = new_age
        self.max_lifespan = max_lifespan
        self.event_label = event_label
        self.on_complete = on_complete
        self.size = size
        self.font = font

        self.time_elapsed = 0.0
        self.phase = "grow"
        self.track_x = size[0] // 4
        self.track_width = (size[0] * 3 / 4) - (size[0] / 4)
        self.track_y = size[1] // 2

    def enter(self, **kwargs):
        self.time_elapsed = 0.0
        self.phase = "grow"
        if self.font is None:
            self.font = PixelFont(scale=2)

    def _age_to_x(self, age):
        return self.track_x + (self.track_width * age / self.max_lifespan)

    @staticmethod
    def _draw_glow_ellipse(surf, center, rx, ry, color):
        cx, cy = round(center[0]), round(center[1])
        rx, ry = max(1, round(rx)), max(1, round(ry))
        gfxdraw.filled_ellipse(surf, cx, cy, rx, ry, color)

    def update(self, dt):
        self.time_elapsed += dt
        if self.phase == "grow" and self.time_elapsed >= self.GROW_DURATION:
            self.phase = "hold"
            self.time_elapsed = 0.0
        elif self.phase == "hold" and self.time_elapsed >= self.HOLD_DURATION:
            if self.on_complete is not None:
                self.on_complete()

    def _current_progress(self):
        if self.phase == "grow":
            t = min(1.0, self.time_elapsed / self.GROW_DURATION)

            t = 1 - (1 - t) ** 3
            return t
        return 1.0

    def draw(self, surface):
        surface.fill(self.BG_COLOR)

        t = self._current_progress()
        current_age = self.prev_age + (self.new_age - self.prev_age) * t

        start_x = self._age_to_x(0)
        prev_x = self._age_to_x(self.prev_age)
        current_x = self._age_to_x(current_age)

        glow_surf = pygame.Surface(surface.get_size())
        glow_surf.fill((0, 0, 0))

        def scaled(color, factor):
            return tuple(min(255, round(c * factor)) for c in color)

        for radius, factor in ((22, 0.10), (14, 0.18), (8, 0.30)):
            gfxdraw.filled_circle(glow_surf, int(current_x), int(self.track_y),
                                  radius, scaled(self.LINE_COLOR, factor))

        surface.blit(glow_surf, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

        pygame.draw.line(surface, (60, 60, 80), (start_x, self.track_y),
                         (start_x + self.track_width, self.track_y), 2)

        if prev_x > start_x:
            pygame.draw.line(surface, (140, 140, 160), (start_x, self.track_y),
                             (prev_x, self.track_y), 3)

        if current_x > prev_x:
            pygame.draw.line(surface, self.LINE_COLOR, (prev_x, self.track_y),
                             (current_x, self.track_y), 4)

        pygame.draw.circle(surface, self.LINE_COLOR, (int(current_x), self.track_y), 8)

        age_text = self.font.render(f"Age {int(current_age)}", True, self.TEXT_COLOR)
        surface.blit(age_text, (current_x - age_text.get_width() // 2, self.track_y - 50))

        if self.phase == "hold" and self.event_label:
            label_alpha = min(255, int(255 * (self.time_elapsed / 0.4)))
            label_surf = self.font.render(self.event_label, True, self.TEXT_COLOR)
            label_surf.set_alpha(label_alpha)
            surface.blit(label_surf, (current_x - label_surf.get_width() // 2, self.track_y + 30))
