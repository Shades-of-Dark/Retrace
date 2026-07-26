import math

import pygame


def find_water_bodies(tilemap, layer=None, diagonal=True):
    """Groups water tiles (raw entries with tileset == "water") into bodies
    of mutually-adjacent tiles via flood fill. Returns a list of bodies, each
    a list of (x, y) tile-grid positions (same units as the raw entry's
    "pos" - multiply by tilemap.tile_size for world pixels).

    layer restricts the scan to one layer id; None (default) pools water
    tiles across all layers. diagonal=True treats 8-directional neighbors as
    connected instead of just the 4 orthogonal ones."""
    water_positions = set()
    for bucket in tilemap.chunks.values():
        for raw in bucket:
            if raw.get("tileset") != "water":
                continue
            if layer is not None and raw.get("layer", 0) != layer:
                continue
            water_positions.add(tuple(raw["pos"]))

    if diagonal:
        offsets = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx, dy) != (0, 0)]
    else:
        offsets = [(1, 0), (-1, 0), (0, 1), (0, -1)]

    visited = set()
    bodies = []
    for start in water_positions:
        if start in visited:
            continue
        visited.add(start)
        stack = [start]
        body = []
        while stack:
            x, y = stack.pop()
            body.append((x, y))
            for dx, dy in offsets:
                neighbor = (x + dx, y + dy)
                if neighbor in water_positions and neighbor not in visited:
                    visited.add(neighbor)
                    stack.append(neighbor)
        bodies.append(body)

    return bodies


class Water:
    def __init__(self, points, surface_points, bounds, tile_size, color=(0, 160, 255, 150), wave_amplitude=0,
                 wave_speed=2, damping=0.94):
        self.points = points
        # Only used to make check_splash's splash strength scale relative to
        # a "normal-sized" (one tile wide) entity - see there.
        self.tile_size = tile_size
        # Its own point list, independent of self.points/the outline - a
        # splash or wave animation can move surface_points[i][1] (they're
        # mutable [x, y] lists, not tuples) frame to frame and draw() just
        # draws whatever's there now, instead of re-deriving "the top" from
        # the current point cloud (which breaks as soon as points move
        # independently and no longer share an exact y).
        self.surface_points = surface_points
        # Each point's resting y, captured once - update() sets displacement
        # relative to this baseline every frame instead of adding on top of
        # whatever the point already drifted to, which is what let the
        # surface wander off unbounded instead of settling into a repeating
        # ripple.
        self._base_y = [p[1] for p in surface_points]
        self.color = color
        # 0 by default - water sits perfectly flat until check_splash
        # disturbs it, then the spring sim in update() settles it back to
        # flat on its own. A nonzero ambient sine here competes with that:
        # the surface is never actually at rest, so there's no flat
        # baseline for a splash to visibly stand out against.
        self.wave_amplitude = wave_amplitude
        self.wave_speed = wave_speed

        # bounds: a coarse pygame.Rect (full tile extents, not the half-tile
        # visual surface) used to cheaply reject entities nowhere near this
        # pond before doing the real per-point surface check in check_splash.
        self.bounds = bounds

        # Splash dynamics: a real discretized 1D wave equation (the classic
        # "two height buffers" ripple technique), not a per-point spring.
        # A spring pulling each point back toward ITS OWN resting position
        # only ever resolves locally, in place - it can't produce a wave
        # that visibly travels away from the impact and bounces off the
        # walls, because there's no mechanism connecting a point's motion to
        # its neighbors' except a slow diffusion. The wave equation is the
        # opposite: a point's acceleration comes only from how curved the
        # surface is around it (neighbors above vs below its own height),
        # with no independent pull to 0 at all - that's what makes a local
        # poke split into two ridges that travel outward at a fixed speed
        # (exactly 1 point per update() call here - see update()), reflect
        # off the pond's edges (clamping the missing out-of-range neighbor
        # to the edge point itself gives a reflection that piles up rather
        # than inverting, like a real wall), and only die out via `damping`,
        # a plain per-step multiplier - not a restoring force.
        self._offset = [0.0] * len(surface_points)
        self._prev_offset = [0.0] * len(surface_points)
        self.damping = damping
        self._submerged = False

        self.time = 0

    def splash(self, x, strength, width):
        """Impulses the surface around world-x `x`. Positive strength dips
        it down (a splash going in), negative pushes it up (a splash coming
        out). width is how far the impulse reaches - points fall off
        linearly to 0 at that distance, so a wider (or faster - see
        check_splash) entity disturbs a wider stretch of surface.

        Sets both _offset and _prev_offset to the same displacement (a pure
        "poke", zero implied velocity between them) rather than just one -
        setting only _offset would read as an instantaneous, very large
        velocity to the wave equation (since velocity here is implicitly
        the difference between the two buffers), which rings/overshoots
        wildly on the very next step instead of splitting cleanly into two
        outward-traveling ridges."""
        if width <= 0:
            return
        for i, point in enumerate(self.surface_points):
            dist = abs(point[0] - x)
            if dist < width:
                offset = strength * (1 - dist / width)
                self._offset[i] += offset
                self._prev_offset[i] += offset

    def _interp(self, ys, x):
        """Interpolates a y-value array aligned with self.surface_points'
        x-coordinates (which never move - only y is ever animated) at
        world-x `x`, clamped to the pond's x-extent."""
        pts = self.surface_points
        if x <= pts[0][0]:
            return ys[0]
        if x >= pts[-1][0]:
            return ys[-1]
        for i in range(len(pts) - 1):
            x0, x1 = pts[i][0], pts[i + 1][0]
            if x0 <= x <= x1:
                t = (x - x0) / (x1 - x0) if x1 != x0 else 0
                return ys[i] + (ys[i + 1] - ys[i]) * t
        return ys[-1]

    def height_at(self, x):
        """Interpolated *current* (possibly rippling) surface y at world-x
        `x`."""
        return self._interp([p[1] for p in self.surface_points], x)

    def resting_height_at(self, x):
        """Interpolated resting surface y at world-x `x` - the pond's
        stable baseline, unaffected by any ongoing ripple. check_splash and
        apply_buoyancy compare against this, not height_at: comparing
        against the animated line let an ongoing ripple crossing a
        stationary entity's feet fire spurious splashes (re-injecting
        energy right as the real one was decaying - the water "never
        settling"), and by the same mechanism could flip _submerged early
        and eat the entity's real exit transition before it actually
        happened (the missing jump-out peak)."""
        return self._interp(self._base_y, x)

    def check_splash(self, entity):
        """Call once per frame with any entity that has .rect and .velocity
        (any core.entity.Entity - not player-specific). Detects the entity
        crossing this pond's *resting* surface at its own x (see
        resting_height_at for why resting, not the live rippling line) and
        fires a splash on the transition frame only (self._submerged tracks
        which side it was on last frame, so a fully-submerged entity doesn't
        re-splash every single frame, and moving around below the surface
        never touches it at all): a dip when it crosses downward into the
        water, a peak when it crosses back out.

        The strength coefficient (0.0284) is calibrated, not arbitrary: with
        Player's default fall_gravity, a straight fall of 4 tiles hits the
        water at ~360px/s, and that's tuned so a one-tile-wide entity peaks
        at a half-tile-deep splash at that speed (given this class's default
        `damping` and this method's `width = entity.rect.width * 1.5` - both
        change the strength->peak-displacement relationship, so re-derive
        this constant if either changes). Scaling by
        entity.rect.width/self.tile_size means a wider entity at the same
        speed splashes proportionally more."""
        if not self.bounds.colliderect(entity.rect):
            self._submerged = False
            return

        surface_y = self.resting_height_at(entity.rect.centerx)
        now_submerged = entity.rect.bottom > surface_y

        if now_submerged != self._submerged:
            strength = 0.04 * abs(entity.velocity.y) * (entity.rect.width / self.tile_size)
            width = entity.rect.width * 1.5
            self.splash(entity.rect.centerx, strength if now_submerged else -strength, width)

        self._submerged = now_submerged

    def apply_buoyancy(self, entity, dt, drag=15.0):
        """Slows entity's SINKING while it's below this pond's current
        surface at its own x - water resistance, not a splash (it never
        touches surface_points/_offset/_velocity, so swimming around under
        the surface doesn't disturb the line itself, only crossing it does -
        that's check_splash's job).

        Only opposes velocity.y > 0 (falling), not <= 0 (rising/jumping) -
        real water drags on both directions, but dragging the rise too means
        a jump taken while still partway underwater comes out weaker than a
        jump taken on land, which reads as broken rather than realistic.
        Leaving Player's jump_velocity untouched by drag keeps a jump the
        same height everywhere, in or out of water.

        drag is how strongly velocity.y gets pulled toward 0 per second once
        fully submerged; the pull scales down for an entity only partially
        dipped in (e.g. just its feet), so wading in doesn't instantly stop
        like hitting a wall."""
        if not self.bounds.colliderect(entity.rect):
            return
        if entity.velocity.y <= 0:
            return
        surface_y = self.resting_height_at(entity.rect.centerx)
        if entity.rect.bottom <= surface_y:
            return
        depth_fraction = min(entity.rect.bottom - surface_y, entity.rect.height) / max(entity.rect.height, 1)
        t = min(1.0, drag * dt * depth_fraction)
        entity.velocity.y *= (1 - t)

    def update(self, dt):
        self.time += dt
        n = len(self._offset)

        # The wave equation at exactly Courant number 1 (1 grid point of
        # travel per call): new = left + right - two-steps-ago, damped.
        # Unlike the rest of this codebase's dt*60-normalized easing, this
        # doesn't scale with dt at all - it's a fixed-step technique (its
        # stability and exact traveling/reflecting behavior both depend on
        # advancing exactly 1 point per call), so it assumes update() is
        # called at a roughly steady rate - true here since retrace.py caps to
        # clock.tick(60). A large one-off dt spike would just look like a
        # skipped simulation tick, not break anything.
        new_offset = [0.0] * n
        for i in range(n):
            left = self._offset[i - 1] if i > 0 else self._offset[i]
            right = self._offset[i + 1] if i < n - 1 else self._offset[i]
            new_offset[i] = (left + right - self._prev_offset[i]) * self.damping
        self._prev_offset, self._offset = self._offset, new_offset

        # damping alone only ever asymptotically approaches 0 - technically
        # settled, but the last stretch is a barely-visible, seemingly
        # endless back-and-forth rather than a clean stop. Once the whole
        # pond's disturbance is small enough that finishing it off faster
        # won't be noticeable, pull both buffers toward 0 with extra decay
        # on top of the normal wave step - NOT an outright reset to exactly
        # 0: even if every individual point's magnitude is sub-pixel, the
        # *shape* of the curve across all the points can still be visibly
        # non-flat, so snapping the whole array to 0 in one frame reads as
        # a pop (curve -> dead flat, instantly) rather than a settle. This
        # keeps shrinking that same shape smoothly down to nothing over a
        # few more frames instead.
        if max(abs(v) for v in self._offset) < 0.5:
            fade = 0.8
            for i in range(n):
                self._offset[i] *= fade
                self._prev_offset[i] *= fade

        for i, (point, base_y) in enumerate(zip(self.surface_points, self._base_y)):
            ambient = self.wave_amplitude * math.sin(self.time * self.wave_speed + point[0] * 0.05)
            point[1] = base_y + ambient + self._offset[i]

    def draw(self, surf, camera=None):
        # self.points is only the sides+bottom of the outline (see
        # create_water) - stitching the current (possibly wavy)
        # surface_points on as the top edge every frame is what keeps the
        # fill polygon attached to the line instead of leaving a gap when
        # the line animates away from its rest position.
        fill_points = self.surface_points + self.points
        points = [camera.apply_pos(p) for p in fill_points] if camera else fill_points

        # pygame.draw.polygon ignores a color's alpha channel when drawing
        # straight onto surf (it's blended per-pixel only when the *source*
        # surface has its own alpha channel) - so semi-transparency needs an
        # SRCALPHA scratch surface drawn on first, then blitted onto surf,
        # rather than passing self.color's alpha to draw.polygon directly.
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        min_x, min_y = min(xs), min(ys)
        w = max(1, round(max(xs) - min_x) + 1)
        h = max(1, round(max(ys) - min_y) + 1)
        local_points = [(x - min_x, y - min_y) for x, y in points]

        layer = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.polygon(layer, self.color, local_points)
        surf.blit(layer, (min_x, min_y))

        if len(self.surface_points) >= 2:
            surface = [camera.apply_pos(p) for p in self.surface_points] if camera else self.surface_points
            pygame.draw.lines(surf, (255, 255, 255), False, surface)


def _trace_outline(pond_set):
    """Walks the exact outer boundary of a union of unit tiles (pond_set:
    a set of (x, y) tile-grid positions) and returns it as an ordered,
    closed ring of tile-grid corner points hugging the tiles' true edges -
    not an approximation from tile centers/centroid-angle sorting. Not yet
    scaled to world pixels - see create_water, which needs these in
    tile-grid units to split out the top edge exactly.

    Each tile contributes a boundary edge (a segment between two of its
    corners) wherever its neighbor on that side isn't part of the pond.
    Those edges are then walked corner-to-corner into a single closed loop."""
    edges = {}

    def add_edge(a, b):
        edges.setdefault(a, set()).add(b)
        edges.setdefault(b, set()).add(a)

    for x, y in pond_set:
        if (x, y - 1) not in pond_set:
            add_edge((x, y), (x + 1, y))  # top edge
        if (x, y + 1) not in pond_set:
            add_edge((x, y + 1), (x + 1, y + 1))  # bottom edge
        if (x - 1, y) not in pond_set:
            add_edge((x, y), (x, y + 1))  # left edge
        if (x + 1, y) not in pond_set:
            add_edge((x + 1, y), (x + 1, y + 1))  # right edge

    if not edges:
        return []

    start = next(iter(edges))
    loop = [start]
    prev, current = None, start
    while True:
        next_corner = next((n for n in edges[current] if n != prev), None)
        if next_corner is None or next_corner == start:
            break
        loop.append(next_corner)
        prev, current = current, next_corner

    return loop


def _surface_span(pond_set):
    """(top_y, left, right) in tile-grid units: the row of the pond's
    exposed top edge (tiles with no water tile directly above them) and
    its x-extent. Shared by _surface_points and create_water's outline
    split so both agree on exactly which corners are "the top edge"."""
    surface_tiles = [(x, y) for x, y in pond_set if (x, y - 1) not in pond_set]
    if not surface_tiles:
        return None
    top_y = min(y for _, y in surface_tiles)
    xs = sorted(x for x, y in surface_tiles if y == top_y)
    return top_y, xs[0], xs[-1] + 1


def _surface_points(tile_size, span, subdivisions=4):
    """The pond's exposed top edge as world-pixel [x, y] points - lists,
    not tuples, so wave/splash code can mutate a point's y in place later.
    subdivisions adds extra points per tile-width (default 4) beyond just
    the two corners, so a wave/ripple animation has enough resolution to
    look like a curve instead of a few widely-spaced points snapping around.

    y sits at tile_size / 2, not the top of the tile - the water tileset's
    art only fills the bottom half of a surface tile (the top half is the
    bank/shore art from the tile above), so the actual water line in-game
    is halfway down the tile, not flush with its top edge. _split_outline's
    side walls still start from the tile's true top corner down to this
    line, which is correct - above the line is bank art, not water, so the
    polygon fill has no business extending up there anyway."""
    if span is None:
        return []
    top_y, left, right = span
    steps = max(1, (right - left) * subdivisions)
    surface_y = top_y * tile_size + tile_size / 2
    return [
        [(left + (right - left) * i / steps) * tile_size, surface_y]
        for i in range(steps + 1)
    ]


def _split_outline(pond_set, span, tile_size):
    """Splits _trace_outline's closed ring into just the sides+bottom, as
    world-pixel points ordered to start right after the top-right corner
    and end right before the top-left corner - i.e. exactly the piece
    Water.draw needs to append after surface_points to close the polygon.
    Falls back to the full outline (old static-top behavior) for shapes
    where the top edge isn't a single clean arc of the ring (e.g. a
    terraced pond) - rare enough not to be worth solving here."""
    loop = _trace_outline(pond_set)
    if not loop or span is None:
        return [(x * tile_size, y * tile_size) for x, y in loop]

    top_y, left, right = span
    top_left, top_right = (left, top_y), (right, top_y)
    if top_left not in loop or top_right not in loop:
        return [(x * tile_size, y * tile_size) for x, y in loop]

    n = len(loop)
    i, j = loop.index(top_left), loop.index(top_right)

    def arc(a, b):
        return loop[a:b + 1] if a <= b else loop[a:] + loop[:b + 1]

    forward = arc(i, j)   # top_left -> ... -> top_right
    backward = arc(j, i)  # top_right -> ... -> top_left

    def is_top_run(points):
        return all(y == top_y for _, y in points)

    if is_top_run(forward):
        body = backward
    elif is_top_run(backward):
        body = list(reversed(forward))
    else:
        # Top edge isn't one clean arc of the ring - bail out to the full
        # static outline rather than guessing at a shape that doesn't fit
        # this assumption.
        return [(x * tile_size, y * tile_size) for x, y in loop]

    return [(x * tile_size, y * tile_size) for x, y in body[1:-1]]


def create_water(water_tiles, tile_size, surface_subdivisions=4):
    """Uses the list of adjacent tiles (ponds/lakes of water) to create water objects and returns a list of water
    objects. tile_size converts the tile-grid outline to world pixels (same convention as
    TileMap._make_entry: pos * tile_size), since Water.draw/camera.apply_pos work in world-pixel space."""
    water_bodies = []
    for pond in water_tiles:
        pond_set = set(pond)
        span = _surface_span(pond_set)
        body_points = _split_outline(pond_set, span, tile_size)
        surface_points = _surface_points(tile_size, span, surface_subdivisions)

        min_x = min(x for x, y in pond_set)
        max_x = max(x for x, y in pond_set)
        min_y = min(y for x, y in pond_set)
        max_y = max(y for x, y in pond_set)
        bounds = pygame.Rect(
            min_x * tile_size, min_y * tile_size,
            (max_x - min_x + 1) * tile_size, (max_y - min_y + 1) * tile_size,
        )

        water_bodies.append(Water(body_points, surface_points, bounds, tile_size))
    return water_bodies
