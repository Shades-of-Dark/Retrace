import pygame


class Entity(pygame.sprite.Sprite):
    """Base for anything with a position, image, and per-frame update.
    Extend it per-game rather than editing it."""

    def __init__(self, pos, size, *groups, color=(255, 255, 255)):
        super().__init__(*groups)
        self.image = pygame.Surface(size, pygame.SRCALPHA)
        self.image.fill(color)
        self.rect = self.image.get_rect(topleft=pos)
        self.pos = pygame.Vector2(pos)
        self.velocity = pygame.Vector2()

    def update(self, dt):
        self.pos += self.velocity * dt
        self.rect.topleft = (round(self.pos.x), round(self.pos.y))

    def move_and_collide(self, dt, solids):
        """Axis-separated movement against a list of pygame.Rects. Returns
        which sides collided this frame, useful for both platformers and
        top-down games."""
        collisions = {"left": False, "right": False, "top": False, "bottom": False}

        self.pos.x += self.velocity.x * dt
        self.rect.x = round(self.pos.x)
        for solid in solids:
            if self.rect.colliderect(solid):
                if self.velocity.x > 0:
                    self.rect.right = solid.left
                    collisions["right"] = True
                elif self.velocity.x < 0:
                    self.rect.left = solid.right
                    collisions["left"] = True
                self.pos.x = self.rect.x

        self.pos.y += self.velocity.y * dt
        self.rect.y = round(self.pos.y)
        for solid in solids:
            if self.rect.colliderect(solid):
                if self.velocity.y > 0:
                    self.rect.bottom = solid.top
                    collisions["bottom"] = True
                elif self.velocity.y < 0:
                    self.rect.top = solid.bottom
                    collisions["top"] = True
                self.pos.y = self.rect.y

        return collisions

    def draw(self, surface, camera=None):
        rect = camera.apply(self.rect) if camera else self.rect
        surface.blit(self.image, rect)
