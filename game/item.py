import pygame
from core.entity import Entity
from core.core_funcs import desaturate_surface, to_alpha_surface


class Item(Entity):
    INTERACT_KEY = pygame.K_e
    INTERACT_RANGE = 20
    PROMPT_COLOR = (243, 243, 243)
    PROMPT_RADIUS = 2
    PROMPT_OFFSET_Y = 8

    # "already checked, not it" treatment for wrong clues: fades toward a
    # muted/gray version over CHECKED_FLASH_DURATION and stays that way,
    # so previously-checked items read at a glance as dismissed.
    CHECKED_FLASH_DURATION = 0.3
    CHECKED_DESATURATION = 0.7

    def __init__(self, image, pos, message, is_correct=False, on_interact=None):
        super().__init__(pos, image.get_size())
        self.message = message
        self.is_correct = is_correct
        self.on_interact = on_interact
        self.in_range = False
        self.image = image
        self.checked_wrong = False
        self.checked_timer = 0.0
        self._alpha_image = None
        self._muted_image = None

    def mark_checked_wrong(self):
        self.checked_wrong = True
        self.checked_timer = 0.0

    def update(self, dt, player_rect=None):

        if player_rect is not None:
            zone = self.rect.inflate(self.INTERACT_RANGE * 2, self.INTERACT_RANGE * 2)
            self.in_range = zone.colliderect(player_rect)

        if self.checked_wrong and self.checked_timer < self.CHECKED_FLASH_DURATION:
            self.checked_timer = min(self.CHECKED_FLASH_DURATION, self.checked_timer + dt)

    def handle_event(self, event):
        if not self.in_range:
            return
        if event.type == pygame.KEYDOWN and event.key == self.INTERACT_KEY:
            if self.on_interact is not None:
                self.on_interact(self)

    def get_alpha_image(self):
        """True per-pixel-alpha version of the base image (source images
        are colorkey-transparent, not SRCALPHA). Cached and shared by
        anything that needs to composite this sprite without relying on
        colorkey surviving a copy()/blit() chain."""
        if self._alpha_image is None:
            self._alpha_image = to_alpha_surface(self.image)
        return self._alpha_image

    def _current_image(self):
        if not self.checked_wrong:
            return self.image
        alpha_image = self.get_alpha_image()
        if self._muted_image is None:
            self._muted_image = desaturate_surface(self.image, self.CHECKED_DESATURATION)
        t = min(1.0, self.checked_timer / self.CHECKED_FLASH_DURATION)
        if t >= 1.0:
            return self._muted_image
        blended = alpha_image.copy()
        overlay = self._muted_image.copy()
        overlay.set_alpha(round(255 * t))
        blended.blit(overlay, (0, 0))
        return blended

    def draw(self, surface, camera=None):
        rect = camera.apply(self.rect) if camera else self.rect
        surface.blit(self._current_image(), rect)
        if self.in_range:
            self._draw_prompt(surface, camera)

    def _draw_prompt(self, surface, camera):
        world_pos = (self.rect.centerx, self.rect.top - self.PROMPT_OFFSET_Y)
        screen_pos = camera.apply_pos(world_pos) if camera else pygame.Vector2(world_pos)
        pygame.draw.circle(surface, self.PROMPT_COLOR, (round(screen_pos.x), round(screen_pos.y)), self.PROMPT_RADIUS)
