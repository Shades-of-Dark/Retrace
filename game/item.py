import pygame
from core.entity import Entity


class Item(Entity):
    INTERACT_KEY = pygame.K_e
    INTERACT_RANGE = 20
    PROMPT_COLOR = (243, 243, 243)
    PROMPT_RADIUS = 2
    PROMPT_OFFSET_Y = 8

    def __init__(self, image, pos, message, is_correct=False, on_interact=None):
        super().__init__(pos, image.get_size())
        self.message = message
        self.is_correct = is_correct
        self.on_interact = on_interact
        self.in_range = False
        self.image = image

    def update(self, dt, player_rect=None):

        if player_rect is not None:
            zone = self.rect.inflate(self.INTERACT_RANGE * 2, self.INTERACT_RANGE * 2)
            self.in_range = zone.colliderect(player_rect)

    def handle_event(self, event):
        if not self.in_range:
            return
        if event.type == pygame.KEYDOWN and event.key == self.INTERACT_KEY:
            if self.on_interact is not None:
                self.on_interact(self)

    def draw(self, surface, camera=None):
        rect = camera.apply(self.rect) if camera else self.rect
        surface.blit(self.image, rect)
        if self.in_range:
            self._draw_prompt(surface, camera)

    def _draw_prompt(self, surface, camera):
        world_pos = (self.rect.centerx, self.rect.top - self.PROMPT_OFFSET_Y)
        screen_pos = camera.apply_pos(world_pos) if camera else pygame.Vector2(world_pos)
        pygame.draw.circle(surface, self.PROMPT_COLOR, (round(screen_pos.x), round(screen_pos.y)), self.PROMPT_RADIUS)
