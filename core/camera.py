import math
import random

import pygame


class Camera:
    """World-space -> screen-space offset with optional smoothing and
    bounds clamping. Works with a target that's a pygame.Rect, an Entity
    (anything with a .rect), or a raw position."""

    def __init__(self, width, height, smoothing=0.1, intro_smoothing=None, intro_settle_distance=6):
        self.width = width
        self.height = height
        self.offset = pygame.Vector2()
        self.smoothing = smoothing
        self.target = None
        self.bounds = None  # optional pygame.Rect limiting the camera in world space

        # Optional slow-pan intro: while the camera is still far from its
        # target (e.g. right after a level loads and offset starts at the
        # origin), it eases in at intro_smoothing instead of the normal
        # (much snappier) smoothing, so the opening pan reads as a
        # deliberate look around the level rather than a jarring snap.
        # Once within intro_settle_distance px of the target it hands off
        # to normal smoothing for the rest of gameplay.
        self.intro_smoothing = intro_smoothing
        self.intro_settle_distance = intro_settle_distance
        self._intro_active = intro_smoothing is not None

        self._shake_elapsed = 0.0
        self._shake_duration = 0.0
        self._shake_intensity = 0.0
        self._shake_randomness = 1.0
        self._shake_angle = 0.0
        self._shake_offset = pygame.Vector2()

    def follow(self, target):
        self.target = target

    def set_bounds(self, rect):
        self.bounds = rect

    def shake(self, intensity, duration, randomness=1.0):
        """Trigger a screen shake. intensity is the max offset in pixels
        (decays to 0 over duration seconds). randomness in [0, 1] blends
        the shake's motion between a smooth circular wobble (0) and fully
        random per-frame jitter (1). Calling this again while a shake is
        already running replaces it outright - it doesn't stack."""
        self._shake_intensity = intensity
        self._shake_duration = duration
        self._shake_elapsed = 0.0
        self._shake_randomness = max(0.0, min(1.0, randomness))

    @property
    def shaking(self):
        return self._shake_elapsed < self._shake_duration

    def _update_shake(self, dt):
        if self._shake_duration <= 0 or self._shake_elapsed >= self._shake_duration:
            self._shake_offset = pygame.Vector2()
            return
        self._shake_elapsed += dt
        falloff = max(0.0, 1.0 - self._shake_elapsed / self._shake_duration)
        magnitude = self._shake_intensity * falloff

        self._shake_angle += dt * 40
        smooth = pygame.Vector2(math.cos(self._shake_angle), math.sin(self._shake_angle))
        jitter = pygame.Vector2(random.uniform(-1, 1), random.uniform(-1, 1))
        direction = smooth.lerp(jitter, self._shake_randomness)
        if direction.length_squared() > 0:
            direction.normalize_ip()
        self._shake_offset = direction * magnitude

    def _target_pos(self):
        target = self.target
        if target is None:
            return None
        if hasattr(target, "rect"):
            target = target.rect
        if isinstance(target, pygame.Rect):
            return pygame.Vector2(target.center)
        return pygame.Vector2(target)

    def update(self, dt):
        target_pos = self._target_pos()
        if target_pos is not None:
            desired = pygame.Vector2(
                target_pos.x - self.width / 2,
                target_pos.y - self.height / 2,
            )
            smoothing = self.smoothing
            if self._intro_active:
                if (desired - self.offset).length() <= self.intro_settle_distance:
                    self._intro_active = False
                else:
                    smoothing = self.intro_smoothing

            if smoothing <= 0:
                self.offset = desired
            else:
                t = min(1.0, smoothing * dt * 60)
                self.offset += (desired - self.offset) * t
            if self.bounds:
                self.offset.x = max(self.bounds.left, min(self.offset.x, self.bounds.right - self.width))
                self.offset.y = max(self.bounds.top, min(self.offset.y, self.bounds.bottom - self.height))
        self._update_shake(dt)

    @property
    def total_offset(self):
        return self.offset + self._shake_offset

    def apply(self, rect):
        total = self.total_offset
        return rect.move(-round(total.x), -round(total.y))

    def apply_pos(self, pos):
        total = self.total_offset
        return pygame.Vector2(pos[0] - total.x, pos[1] - total.y)

    def screen_to_world(self, pos):
        total = self.offset + self._shake_offset
        return pygame.Vector2(pos[0] + total.x, pos[1] + total.y)
