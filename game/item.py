import pygame
from core.entity import Entity


def interact(events):
    for event in events:
        if event.key == pygame.K_e:
            return True


class Item(Entity):

    def __init__(self, image, pos, size,message, *groups):
        super().__init__(pos, size, *groups)
        self.pos = pos
        self.image = image
        self.message = message

    def update(self, event_list):
        if interact(event_list):
            pass
