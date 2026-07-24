import math
import os
import random

import pygame

FRAME_SIZE = 16
BLADES_PER_TILE = (4, 7)
X_JITTER = FRAME_SIZE // 2  # blade frames are tile-sized, so without this every


def load_grass_frames(tilesets_dir, filename="grass.png"):
    """Slices grass.png (its blade variants laid out side by side,
    FRAME_SIZE wide each) into individual surfaces, using the same
    black-colorkey transparency convention as the rest of tilesets_dir."""
    sheet = pygame.image.load(os.path.join(tilesets_dir, filename)).convert()
    sheet.set_colorkey((0, 0, 0))
    count = sheet.get_width() // FRAME_SIZE
    return [
        sheet.subsurface((i * FRAME_SIZE, 0, FRAME_SIZE, sheet.get_height())).copy()
        for i in range(count)
    ]


RESTORING_FACTOR = 0.7

# angle=0 is upright (90 deg from the ground); angle=90 would lay the blade
# fully flat (0 deg from the ground, clipping into the tile below it). Cap it
# short of that so the blade always keeps HORIZONTAL_MARGIN degrees above
# horizontal even at the hardest bend.
HORIZONTAL_MARGIN = 25  # tune between 10-20
MAX_BEND_ANGLE = 90 - HORIZONTAL_MARGIN

# "Close enough to upright" (degrees) that play.py can stop calling
# bend_towards on this blade - lets it know when a tile that's no longer
# near the player has actually finished easing back, instead of tracking
# it forever waiting for angle to hit exactly 0 asymptotically.
SETTLE_EPSILON = 0.5

# Ambient sway - a gentle, purely visual sine wobble applied on top of
# self.angle at draw time (never written into self.angle/target_angle
# itself), so blades the player never touches still have some life instead
# of standing perfectly rigid, without that costing a bend_towards() call
# per blade every frame (which is exactly what play.py's active-tile
# tracking exists to avoid). WIND_PHASE_SCALE keys each blade's phase off
# its own root x, so neighboring blades sway slightly out of sync - reads
# as a wave passing through the field instead of every blade snapping back
# and forth in lockstep. Independent of game/wind.py's gusts - this sway
# happens everywhere, all the time, gusts are an extra, localized push on
# top of it.
WIND_AMPLITUDE = 6
WIND_SPEED = 1.5  # base angular speed (rad/s) - see sway_phase_delta
WIND_PHASE_SCALE = 0.05

# How strongly a gust (see game/wind.py) bends a blade, in degrees per
# px/s of gust speed - e.g. a speed-120 gust contributes 120*0.15 = 18
# degrees of average lean. GUST_MAX_ANGLE caps the *total* drawn angle
# (player bend + ambient sway + gust), independently of MAX_BEND_ANGLE
# (which only governs the player-interaction physics angle) - without a
# shared cap, several effects stacking at once could rotate a blade past
# horizontal and it'd visibly flip/invert instead of just leaning hard.
GUST_BEND_SCALE = 0.15
GUST_MAX_ANGLE = 80

# On top of that average lean, a gust also makes the sway swing back and
# forth faster - NOT bigger (WIND_AMPLITUDE stays fixed): rad/s of extra
# angular speed per px/s of gust speed. See sway_phase_delta for why this
# has to be integrated over time rather than just plugged into
# sin(time * speed) directly - speed itself changes as gusts come and go.
GUST_SWAY_SPEED_BOOST = 0.02


def sway_phase_delta(dt, gust_speed):
    """How much to advance the shared sway phase this frame (see
    play.py's self.sway_phase, passed into every blade's draw() as
    sway_phase). Angular speed is WIND_SPEED, boosted by the current gust
    (abs(gust_speed) is the same value for every blade this frame - see
    WindField.screen_speed).

    This can't just be "sin(time * current_speed)" the way a constant-speed
    sway could - if the multiplier changes frame to frame (as it does the
    moment a gust starts or stops), the sine argument jumps discontinuously
    even though the phase actually reached so far didn't change, which
    would visibly kink the sway. Integrating the *rate* into an
    accumulating phase (this function's job) instead means the speed can
    change freely between frames without ever discontinuing the motion
    already in progress."""
    return (WIND_SPEED + GUST_SWAY_SPEED_BOOST * abs(gust_speed)) * dt


class Grass(pygame.sprite.Sprite):
    """A single grass-blade instance. spawn_for_tile scatters several of
    these - random position, random blade variant - across one tile instead
    of drawing that tile's flat static image."""

    def __init__(self, image, angle, pos):
        super().__init__()
        self.angle = angle
        self.surf = image
        self.image = image
        self.rect = self.image.get_rect(topleft=(pos[0], pos[1]))
        self.target_angle = 0

        # The blade art doesn't necessarily fill its frame - grass.png's
        # frames are 32px tall but the visible pixels only occupy the top
        # ~16px, so treating the frame's own bottom edge as the root (as if
        # content == frame) plants it a half-frame below where it's actually
        # drawn. Find the real content instead of assuming.
        content = image.get_bounding_rect()
        self.root = (self.rect.left + content.centerx, self.rect.top + content.bottom)
        self._center_offset = pygame.Vector2(
            content.centerx - image.get_width() / 2,
            content.bottom - image.get_height() / 2,
        )

    @staticmethod
    def _base_width(frame, content):
        """Width of the blade's actual base - just the bottom couple pixels
        of its visible content, not the whole silhouette. A blade that fans
        out wider above its root would otherwise report a base far wider
        than where it actually plants into the ground (these blades' bases
        are only ~2-4px, well under content's full width)."""
        strip_height = min(2, content.height)
        strip = frame.subsurface(pygame.Rect(content.left, content.bottom - strip_height, content.width, strip_height))
        return max(1, strip.get_bounding_rect().width)

    @classmethod
    def spawn_for_tile(cls, tile_rect, frames, count=None):
        """count defaults to a random pick in BLADES_PER_TILE. Each blade
        gets a random frame and a random offset from the tile's top-left -
        frames are tile-sized, so without an offset every blade in a tile
        would land on the exact same spot. The x offset is rejection-sampled
        against already-placed blades' base widths (see _base_width) so two
        blades' roots never land close enough to overlap into one blob;
        after a few failed attempts a blade is skipped rather than forced
        into an overlapping spot."""
        blades = []
        placed = []  # (root_x, half_base_width) for blades already placed in this tile
        for _ in range(count if count is not None else random.randint(*BLADES_PER_TILE)):
            frame = random.choice(frames)
            content = frame.get_bounding_rect()
            half_width = cls._base_width(frame, content) / 2

            root_x = None
            for _attempt in range(10):
                candidate_x = tile_rect.centerx + random.randint(-X_JITTER, X_JITTER)

                candidate_x = max(tile_rect.left, min(tile_rect.right, candidate_x))
                if all(abs(candidate_x - px) >= half_width + p_half for px, p_half in placed):
                    root_x = candidate_x
                    break
            if root_x is None:
                continue

            # Solve for the topleft that puts the blade's actual visible
            # root (content.centerx/content.bottom, not the frame's raw
            # corner) at the tile's bottom - i.e. the ground surface.
            desired_root = (root_x, tile_rect.bottom)
            pos = (desired_root[0] - content.centerx, desired_root[1] - content.bottom)
            blades.append(cls(frame, 0, pos))
            placed.append((root_x, half_width))
        return blades

    def bend_towards(self, entity, dt):
        """Leans away from entity, strongest when entity is right on top of
        this blade's root (self.root - the point it's rooted at and pivots
        around) and fading to upright by BEND_RADIUS away. Distance is true
        2D (entity's feet to the blade's root), not just horizontal, so an
        entity on a platform at a different height doesn't bend grass that's
        actually far above/below it."""
        root_x, root_y = self.root
        gate_radius = 20  # must match the "< 20" distance gate below - the
                           # push has to reach exactly 0 at that boundary, or
                           # there's a band just inside the gate where the
                           # formula has already flipped sign and leans the
                           # blade toward the entity instead of away
        push_slope = 50 / gate_radius
        if abs(entity.rect.bottom - root_y) < gate_radius:
            rect_pos = [entity.rect.center[0], entity.rect.bottom]
            distance = math.sqrt((rect_pos[0] - root_x) ** 2 + (rect_pos[1] - root_y) ** 2)
            h_dis = rect_pos[0] - root_x
            if distance < gate_radius:
                temp_target = 0
                if h_dis <= 0:
                    temp_target = -50 - h_dis * push_slope
                if h_dis > 0:
                    temp_target = 50 - h_dis * push_slope
                self.target_angle = min(self.target_angle + temp_target, MAX_BEND_ANGLE)
                self.target_angle = max(self.target_angle, -MAX_BEND_ANGLE)
            else:
                self.target_angle = 0

        # dt * 60 normalizes to the tuning done at 60fps (was a bare /3 per
        # call) - so easing speed stays the same in real time regardless of
        # framerate instead of only converging in a fixed number of frames.
        t = min(1.0, dt * 60 / 3)
        self.angle += (self.target_angle - self.angle) * t
        if self.settled:
            # Exact 0, not just close - "+= (target-angle)*t" only ever
            # asymptotically approaches upright, it never actually gets
            # there on its own.
            self.angle = 0
            self.target_angle = 0

    @property
    def settled(self):
        """True once this blade is close enough to upright, and isn't being
        pushed away from it, that play.py can stop calling bend_towards on
        it - lets a tile drop out of active tracking once its blades have
        genuinely finished easing back, not just because the player moved
        on."""
        return abs(self.angle) < SETTLE_EPSILON and abs(self.target_angle) < SETTLE_EPSILON

    def draw(self, surf, camera=None, sway_phase=0, gust_speed=0):
        """sway_phase: the shared, pre-integrated sway clock - play.py
        accumulates this once per frame via sway_phase_delta(dt, gust_speed)
        and passes the same value to every blade, rather than each blade
        computing time*speed itself (see sway_phase_delta for why - gust
        speed changing the sway's rate needs proper integration, not a
        direct multiply). gust_speed: signed px/s, also the SAME value for
        every blade drawn this frame - e.g. game/wind.py's
        WindField.screen_speed(). Deliberately not position-dependent:
        bending only whatever's directly under a gust's own (possibly much
        narrower than the screen) width reads as a thin line sweeping
        across, not wind moving through the whole scene - so every visible
        blade reacts together while a gust is anywhere on screen.

        The ambient sway stays per-blade (keyed off root[0], added to the
        shared phase) so it still reads as a wave, not a lockstep wobble.
        Both sway and gust_bend are purely rendering-time offsets, added
        here and never folded into self.angle - so neither can affect
        `settled` (which only looks at the player-interaction state) or
        cause a blade to be treated as still bending when it's actually
        just swaying/gusting."""
        sway = WIND_AMPLITUDE * math.sin(sway_phase + self.root[0] * WIND_PHASE_SCALE)
        gust_bend = -gust_speed * GUST_BEND_SCALE

        wind_angle = self.angle + sway + gust_bend
        wind_angle = max(-GUST_MAX_ANGLE, min(GUST_MAX_ANGLE, wind_angle))

        self.image = pygame.transform.rotate(self.surf, wind_angle)
        # rotate() spins around the image's center. Re-anchoring the rotated
        # bounding box's own midbottom pins a different point than the
        # actual root once the content is tilted - the blade visibly
        # floats/drifts instead of pivoting from where it's planted.
        # Instead, rotate the fixed center->root offset (self._center_offset,
        # from the real visible content, not the frame's raw corner) by the
        # same angle and solve for where the rotated image's center must sit
        # so the root pixel itself stays fixed in world space.
        offset = self._center_offset.rotate(-wind_angle)
        center = (self.root[0] - offset.x, self.root[1] - offset.y)
        blit_rect = self.image.get_rect(center=center)
        rect = camera.apply(blit_rect) if camera else blit_rect
        surf.blit(self.image, rect)
