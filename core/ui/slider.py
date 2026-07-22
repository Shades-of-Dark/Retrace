import pygame

from .base import UIElement
from .theme import DEFAULT_THEME


class Slider(UIElement):
    def __init__(self, rect, min_value=0.0, max_value=1.0, value=None, on_change=None, theme=None):
        super().__init__(rect)
        self.min_value = min_value
        self.max_value = max_value
        self.value = value if value is not None else min_value
        self.on_change = on_change
        self.theme = theme or DEFAULT_THEME
        self.dragging = False
        self.handle_radius = self.rect.height // 2 + 2

    def _value_to_x(self):
        t = (self.value - self.min_value) / (self.max_value - self.min_value)
        return self.rect.left + t * self.rect.width

    def _x_to_value(self, x):
        t = max(0.0, min(1.0, (x - self.rect.left) / self.rect.width))
        return self.min_value + t * (self.max_value - self.min_value)

    def set_value(self, value):
        value = max(self.min_value, min(self.max_value, value))
        if value != self.value:
            self.value = value
            if self.on_change:
                self.on_change(self.value)

    def handle_event(self, event):
        if not (self.visible and self.enabled):
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            handle_x = self._value_to_x()
            mx, my = event.pos
            near_handle = (mx - handle_x) ** 2 + (my - self.rect.centery) ** 2 <= self.handle_radius ** 2
            if near_handle or self.rect.collidepoint(event.pos):
                self.dragging = True
                self.set_value(self._x_to_value(mx))
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self.set_value(self._x_to_value(event.pos[0]))

    def draw(self, surface):
        if not self.visible:
            return
        track_rect = pygame.Rect(self.rect.left, self.rect.centery - 2, self.rect.width, 4)
        pygame.draw.rect(surface, self.theme["track"], track_rect, border_radius=2)
        handle_x = self._value_to_x()
        color = self.theme["accent"] if self.enabled else self.theme["text_disabled"]
        pygame.draw.circle(surface, color, (round(handle_x), self.rect.centery), self.handle_radius)
