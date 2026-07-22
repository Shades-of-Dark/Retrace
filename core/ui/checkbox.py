import pygame

from .base import UIElement
from .theme import DEFAULT_THEME


class Checkbox(UIElement):
    def __init__(self, rect, checked=False, on_change=None, theme=None):
        super().__init__(rect)
        self.checked = checked
        self.on_change = on_change
        self.theme = theme or DEFAULT_THEME

    def handle_event(self, event):
        if not (self.visible and self.enabled):
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.checked = not self.checked
                if self.on_change:
                    self.on_change(self.checked)

    def draw(self, surface):
        if not self.visible:
            return
        pygame.draw.rect(surface, self.theme["bg"], self.rect, border_radius=3)
        pygame.draw.rect(surface, self.theme["border"], self.rect, width=1, border_radius=3)
        if self.checked:
            inset = self.rect.inflate(-6, -6)
            color = self.theme["accent"] if self.enabled else self.theme["text_disabled"]
            pygame.draw.rect(surface, color, inset, border_radius=2)
