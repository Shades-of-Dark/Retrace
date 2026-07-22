import pygame

from .base import UIElement
from .theme import DEFAULT_THEME


class Panel(UIElement):
    """A simple container: draws a background box and forwards
    events/update/draw to child UIElements."""

    def __init__(self, rect, theme=None, draw_background=True):
        super().__init__(rect)
        self.theme = theme or DEFAULT_THEME
        self.draw_background = draw_background
        self.children = []

    def add(self, child):
        self.children.append(child)
        return child

    def handle_event(self, event):
        if not (self.visible and self.enabled):
            return
        for child in self.children:
            child.handle_event(event)

    def update(self, dt):
        if not self.visible:
            return
        for child in self.children:
            child.update(dt)

    def draw(self, surface):
        if not self.visible:
            return
        if self.draw_background:
            pygame.draw.rect(surface, self.theme["bg"], self.rect, border_radius=6)
            pygame.draw.rect(surface, self.theme["border"], self.rect, width=1, border_radius=6)
        for child in self.children:
            child.draw(surface)
