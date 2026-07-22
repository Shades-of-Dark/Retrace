import pygame


class UIElement:
    """Base for all UI widgets. Subclasses override handle_event/update/draw."""

    def __init__(self, rect):
        self.rect = pygame.Rect(rect)
        self.visible = True
        self.enabled = True

    def handle_event(self, event):
        pass

    def update(self, dt):
        pass

    def draw(self, surface):
        pass
