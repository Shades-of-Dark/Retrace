import math

from core.entity import Entity


class Player(Entity):
    """Platformer movement on top of Entity's rect/collision plumbing.

    A jump is authored as "how high" and "how long to get there"
    (jump_height/time_to_apex) rather than a hand-picked velocity+gravity
    pair - time_to_apex IS your hang-time knob: raise it for a longer,
    floatier rise. fall_gravity_scale then controls how much snappier the
    fall is than the rise (1.0 = symmetric arc, higher = faster fall).
    Changing either derives a new jump_velocity/gravity via set_jump().
    """

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

    def set_jump(self, jump_height, time_to_apex):
        """jump_height: peak rise in pixels above the takeoff point.
        time_to_apex: seconds from takeoff to the top of the arc."""
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

    def physics_update(self, dt, tile_size, move_x, jump_pressed, solids, ramps):
        """One frame of platformer physics: horizontal accel/friction,
        gravity, collision against `solids`, coyote time, and jumping.
        Returns move_and_collide's per-side collision dict."""
        self._move(dt, move_x)
        self._apply_gravity(dt)
        collisions = self.move_and_collide(dt, solids)

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
                    # move_and_collide() always mirrors rect corrections back
                    # into self.pos (the float position everything else is
                    # integrated from) - skipping that here left pos stale,
                    # so next frame's gravity/movement recomputed rect from
                    # the old sunk-in pos and undid this snap, then got
                    # corrected again the frame after: a clip-in/pop-out
                    # flicker every frame while standing on the ramp.
                    self.pos.y = self.rect.y
                    if self.velocity.y > 0:
                        self.velocity.y = 0
                        self._coyote_timer = self.coyote_time
        if jump_pressed and self.can_jump:
            self.jump()

        return collisions
