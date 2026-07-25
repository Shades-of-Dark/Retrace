import math

import pygame

from core.animation import Animation, Animator, slice_spritesheet
from core.entity import Entity

PLAYER_SPRITES_DIR = "game/assets/images/player"


def _load_frames(filename, frame_size=(16, 16)):
    sheet = pygame.image.load(f"{PLAYER_SPRITES_DIR}/{filename}").convert_alpha()
    return slice_spritesheet(sheet, *frame_size)


def _load_animation(filename, frame_size=(16, 16), frame_duration=0.1, loop=True):
    return Animation(_load_frames(filename, frame_size), frame_duration=frame_duration, loop=loop)


class Player(Entity):

    def __init__(self, pos, size, color=(255, 255, 255), *,
                 acceleration=1800, max_speed=120, deceleration=1800,
                 jump_height=64, time_to_apex=0.45, fall_gravity_scale=1.6,
                 max_fall_speed=500, coyote_time=0.4):
        super().__init__(pos, size, color=color)
        self.acceleration = acceleration
        self.max_speed = max_speed
        self.deceleration = deceleration
        self.max_fall_speed = max_fall_speed
        self.coyote_time = coyote_time
        self.fall_gravity_scale = fall_gravity_scale
        self._coyote_timer = 0.0
        self.set_jump(jump_height, time_to_apex)

        self.facing = 1  # 1 = right, -1 = left
        self._was_grounded = True


        fall_frame, land_frame = _load_frames("player_land.png")

        self.animator = Animator()
        self.animator.add("idle", _load_animation("player_idle.png", frame_duration=0.55))
        self.animator.add("run", _load_animation("player_run.png", frame_duration=0.07, frame_size=(16,17)))
        self.animator.add("jump", _load_animation("player_jump.png"))
        self.animator.add("fall", Animation([fall_frame], loop=True))
        self.animator.add("land", Animation([land_frame], frame_duration=0.15, loop=False))
        self.animator.play("idle")
        self.image = self.animator.image

    def set_jump(self, jump_height, time_to_apex):

        self.jump_height = jump_height
        self.time_to_apex = time_to_apex
        self.jump_velocity = -2 * jump_height / time_to_apex
        self.rise_gravity = 2 * jump_height / time_to_apex ** 2
        self.fall_gravity = self.rise_gravity * self.fall_gravity_scale

    @property
    def can_jump(self):
        return self._coyote_timer > 0

    def jump(self):
        self.velocity.y = self.jump_velocity
        self._coyote_timer = 0.0

    def _move(self, dt, move_x):
        if move_x != 0:
            self.velocity.x += move_x * self.acceleration * dt
            self.velocity.x = max(-self.max_speed, min(self.max_speed, self.velocity.x))
        elif self.velocity.x != 0:

            step = self.deceleration * dt
            if step >= abs(self.velocity.x):
                self.velocity.x = 0
            else:
                self.velocity.x -= math.copysign(step, self.velocity.x)

    def _apply_gravity(self, dt):
        gravity = self.rise_gravity if self.velocity.y < 0 else self.fall_gravity
        self.velocity.y = min(self.velocity.y + gravity * dt, self.max_fall_speed)

    def _touching_ground(self, solids, ramps):

        probe = self.rect.move(0, 1)
        if any(probe.colliderect(solid) for solid in solids):
            return True
        return any(probe.colliderect(ramp.rect) for ramp in ramps)

    def physics_update(self, dt, tile_size, move_x, jump_pressed, solids, ramps):
        """One frame of platformer physics: horizontal accel/friction,
        gravity, collision against `solids`, coyote time, and jumping.
        Returns move_and_collide's per-side collision dict."""
        self._move(dt, move_x)
        self._apply_gravity(dt)
        collisions = self.move_and_collide(dt, solids)

        grounded = collisions["bottom"] or self._touching_ground(solids, ramps)

        if collisions["bottom"]:
            self.velocity.y = 0
            self._coyote_timer = self.coyote_time
        elif collisions["top"]:
            self.velocity.y = 0
        else:
            self._coyote_timer -= dt
        for ramp in ramps:
            hitbox = ramp.rect
            if self.rect.colliderect(hitbox):
                rel_x = self.rect.x - hitbox.x

                if ramp.ramp == 1:
                    pos_height = rel_x + self.rect.width
                elif ramp.ramp == 2:
                    pos_height = tile_size - rel_x

                pos_height = min(pos_height, tile_size)
                pos_height = max(pos_height, 0)

                target_y = hitbox.y + tile_size - pos_height
                if self.rect.bottom > target_y:
                    self.rect.bottom = target_y
                    grounded = True

                    self.pos.y = self.rect.y
                    if self.velocity.y > 0:
                        self.velocity.y = 0
                        self._coyote_timer = self.coyote_time
        if jump_pressed and self.can_jump:
            self.jump()

        self._update_animation(dt, grounded)

        return collisions

    def _update_animation(self, dt, grounded):
        moving = abs(self.velocity.x) > 1
        if moving:
            self.facing = 1 if self.velocity.x > 0 else -1


        if self.velocity.y < 0:
            self.animator.play("jump")
        elif not grounded:
            self.animator.play("fall")
        elif not self._was_grounded:
            self.animator.play("land", restart=True)
        elif self.animator.current_name != "land" or self.animator.animations["land"].done:
            self.animator.play("run" if moving else "idle")

        self._was_grounded = grounded
        self.animator.update(dt)

        frame = self.animator.image
        self.image = frame if self.facing > 0 else pygame.transform.flip(frame, True, False)
