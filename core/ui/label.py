import pygame

from .base import UIElement
from .pixel_font import PixelFont
from .theme import DEFAULT_THEME


class Label(UIElement):
    def __init__(self, pos, text="", font=None, color=None, theme=None):
        self.theme = theme or DEFAULT_THEME
        self.font = font or PixelFont(scale=2)
        self.color = color or self.theme["text"]
        self.text = text
        self._pos = pos
        surf = self.font.render(text, True, self.color)
        super().__init__(surf.get_rect(topleft=pos))

    def draw(self, surface):
        if not self.visible:
            return
        label = self.font.render(self.text, True, self.color)
        surface.blit(label, self._pos)
