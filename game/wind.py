import random


class Gust:
    """A band of wind blowing left across the level at a constant speed -
    just a moving [left, right) span in world-pixel x plus that speed.
    Not tied to grass or any other consumer; WindField.speed_at(x) is the
    generic query surface everything else should use."""

    def __init__(self, left, right, speed):
        self.left = left
        self.right = right
        self.speed = speed  # px/s, always positive - direction is implicit (always left)

    def update(self, dt):
        self.left -= self.speed * dt
        self.right -= self.speed * dt

    def contains(self, x):
        return self.left <= x <= self.right


class WindField:
    """Owns a set of gusts, spawning new ones just off the camera's right
    edge every so often and dropping ones that have fully scrolled off the
    left - and exposes speed_at(x), a plain world-space query any effect
    can use (grass sway, water surface, particles, foliage, whatever else
    later) without knowing anything about Gust or how gusts are managed.

    width_range/speed_range/spawn_interval_range are (min, max) tuples for
    random.uniform/randint - tune per level if the default feel is wrong
    for a particular scene."""

    # How fast smoothed_screen_speed chases screen_speed's raw target, in
    # 1/seconds - e.g. 3.0 covers roughly 95% of the gap in about a second.
    # Without this, a consumer reading screen_speed() directly sees it jump
    # from 0 to full speed (or back) the instant a gust's edge crosses the
    # camera boundary, which reads as a snap instead of wind arriving/dying
    # down.
    EASE_RATE = 3.0

    def __init__(self, tile_size, width_range=(3, 6), speed_range=(80, 160), spawn_interval_range=(4, 8)):
        self.tile_size = tile_size
        self.width_range = width_range
        self.speed_range = speed_range
        self.spawn_interval_range = spawn_interval_range
        self.gusts = []
        self._spawn_timer = random.uniform(*spawn_interval_range)
        self.smoothed_screen_speed = 0.0

    def update(self, dt, camera_rect):
        self._spawn_timer -= dt
        if self._spawn_timer <= 0:
            self._spawn_timer = random.uniform(*self.spawn_interval_range)
            width = random.randint(*self.width_range) * self.tile_size
            speed = random.uniform(*self.speed_range)
            left = camera_rect.right
            self.gusts.append(Gust(left, left + width, speed))

        for gust in self.gusts:
            gust.update(dt)
        # Fully off-screen to the left (camera_rect.left, not some fixed
        # level bound) - a gust that's scrolled past the visible area can no
        # longer affect anything on-screen, regardless of how big the level
        # is beyond that.
        self.gusts = [g for g in self.gusts if g.right > camera_rect.left]

        t = min(1.0, self.EASE_RATE * dt)
        self.smoothed_screen_speed += (self.screen_speed(camera_rect) - self.smoothed_screen_speed) * t

    def speed_at(self, x):
        """Signed wind speed at world-x `x` right now: negative means
        blowing left (the only direction gusts move today), 0 if no gust
        currently covers this x. Sums every overlapping gust, so two gusts
        crossing paths briefly blow harder together rather than one just
        overriding the other."""
        return -sum(g.speed for g in self.gusts if g.contains(x))

    def screen_speed(self, camera_rect):
        """Signed wind speed to apply uniformly across the whole visible
        screen right now: sums every gust currently overlapping
        camera_rect at all, ignoring where exactly within it - for a
        consumer that wants everything on screen reacting together while a
        gust passes through (e.g. every blade of grass bending as one),
        rather than only whatever's directly under the gust's own
        (possibly much narrower than the screen) width, which reads as a
        thin line sweeping across instead of wind moving through the
        scene."""
        return -sum(g.speed for g in self.gusts if g.right > camera_rect.left and g.left < camera_rect.right)
