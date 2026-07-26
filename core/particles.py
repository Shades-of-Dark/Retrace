import random

import pygame


class Particle:
    __slots__ = ("pos", "velocity", "gravity", "color", "size", "lifetime", "age", "fade", "glow")

    def __init__(self, pos, velocity, gravity, color, size, lifetime, fade=True, glow=False):
        self.pos = pygame.Vector2(pos)
        self.velocity = pygame.Vector2(velocity)
        self.gravity = gravity
        self.color = color
        self.size = size
        self.lifetime = lifetime
        self.age = 0.0
        self.fade = fade
        self.glow = glow

    @property
    def alive(self):
        return self.age < self.lifetime

    def update(self, dt):
        self.age += dt
        self.velocity.y += self.gravity * dt
        self.pos += self.velocity * dt

    def draw(self, surface, camera=None):
        life_ratio = max(0.0, 1 - self.age / self.lifetime) if self.fade else 1.0
        size = max(1, round(self.size * life_ratio))
        pos = camera.apply_pos(self.pos) if camera else self.pos
        has_alpha = len(self.color) == 4
        alpha = (int(self.color[3] * life_ratio) if self.fade else self.color[3]) if has_alpha else 255
        rgb = self.color[:3]

        if self.glow and alpha > 0:
            radius = size * 2
            glow_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            for r, factor in ((radius, 0.08), (max(1, round(radius * 0.5)), 0.15)):
                pygame.draw.circle(glow_surf, (*rgb, round(alpha * factor)), (radius, radius), r)
            surface.blit(glow_surf, (pos.x - radius, pos.y - radius), special_flags=pygame.BLEND_RGBA_ADD)

        if has_alpha:
            surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*rgb, alpha), (size, size), size)
            surface.blit(surf, (pos.x - size, pos.y - size))
        else:
            pygame.draw.circle(surface, self.color, (round(pos.x), round(pos.y)), size)


class ParticleSystem:
    """Emits particles from presets the game layer registers - core stays
    ignorant of what a preset means (sparks, dust, blood, confetti...).

    Preset config keys (each may be a fixed value or a (min, max) tuple):
        count, speed, angle, gravity, color, size, lifetime, fade, glow
    """

    def __init__(self):
        self.presets = {}
        self.particles = []

    def register_preset(self, name, config):
        self.presets[name] = config

    def emit(self, name, pos, **overrides):
        config = {**self.presets[name], **overrides}

        def resolve(key, default):
            value = config.get(key, default)
            return random.uniform(*value) if isinstance(value, tuple) else value

        count = config.get("count", 1)
        count = random.randint(*count) if isinstance(count, tuple) else count

        for _ in range(count):
            speed = resolve("speed", 0)
            angle = resolve("angle", 0)
            size = resolve("size", 2)
            lifetime = resolve("lifetime", 0.5)

            direction = pygame.Vector2(1, 0).rotate(angle)
            self.particles.append(Particle(
                pos=pos,
                velocity=direction * speed,
                gravity=config.get("gravity", 0),
                color=config.get("color", (255, 255, 255)),
                size=size,
                lifetime=lifetime,
                fade=config.get("fade", True),
                glow=config.get("glow", False),
            ))

    def update(self, dt):
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.alive]

    def draw(self, surface, camera=None):
        for p in self.particles:
            p.draw(surface, camera)

    def clear(self):
        self.particles.clear()
