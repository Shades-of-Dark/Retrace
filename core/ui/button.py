import pygame

from .base import UIElement
from .pixel_font import PixelFont
from .theme import DEFAULT_THEME


class Button(UIElement):
    def __init__(self, rect, text="", on_click=None, font=None, theme=None):
        super().__init__(rect)
        self.text = text
        self.on_click = on_click
        self.font = font or PixelFont(scale=2)
        self.theme = theme or DEFAULT_THEME
        self.hovered = False
        self.pressed = False

    def handle_event(self, event):
        if not (self.visible and self.enabled):
            return
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.pressed = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.pressed and self.rect.collidepoint(event.pos) and self.on_click:
                self.on_click()
            self.pressed = False

    def draw(self, surface):
        if not self.visible:
            return
        if not self.enabled:
            color = self.theme["bg"]
        elif self.pressed:
            color = self.theme["bg_pressed"]
        elif self.hovered:
            color = self.theme["bg_hover"]
        else:
            color = self.theme["bg"]

        pygame.draw.rect(surface, color, self.rect, border_radius=4)
        pygame.draw.rect(surface, self.theme["border"], self.rect, width=1, border_radius=4)

        text_color = self.theme["text"] if self.enabled else self.theme["text_disabled"]
        label = self.font.render(self.text, True, text_color)
        surface.blit(label, label.get_rect(center=self.rect.center))
