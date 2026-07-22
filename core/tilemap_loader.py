"""
Connects the editor's level format (core/pygame_loader.py) to the rest of the
toolkit: draws in the same (surface, camera_offset) style as Entity.draw and
Camera, and turns specific layers into AABB collision rects your game code
can hand to a physics/movement system.

pygame_loader.TileMap already does the hard part (chunked lookup, tileset
scaling, layer visibility). This file doesn't reimplement any of that - it
just wraps it so `game/` code has one obvious entry point instead of poking
at TileMap/TileEntry directly.

Usage:
    from core.tilemap_loader import Level

    level = Level.load("assets/levels/level1.json", tilesets_dir="assets/tilesets")

    # each frame, camera_rect is your Camera's current world-space view
    level.draw(screen, camera_rect, camera_offset=(camera_rect.x, camera_rect.y))

    solids = level.get_solid_rects(camera_rect)
    for rect in solids:
        if player.rect.colliderect(rect):
            ...  # resolve collision

    for entry in level.get_ramps(camera_rect):
        ...  # entry.ramp: 1 = up-right, 2 = up-left (see pygame_loader docstring)

    spawn = level.get_spawn_point()  # world-pixel pygame.Vector2, from the
                                      # "player_spawn" entity placed in the editor
"""

import pygame

from core.pygame_loader import TileMap


class Level:
    """
    Thin wrapper around a loaded TileMap.

    Which layers are solid is read straight from the level file's
    layer_collision data (the editor's per-layer "solid" toggle) via
    tilemap.solid_layers - not something the game has to specify.
    """

    def __init__(self, tilemap: TileMap):
        self.tilemap = tilemap

    @property
    def solid_layers(self):
        return self.tilemap.solid_layers

    @classmethod
    def load(cls, level_path, tilesets_dir="assets/tilesets"):
        tilemap = TileMap.load(level_path, tilesets_dir=tilesets_dir)
        return cls(tilemap)

    def get_spawn_point(self, kind="player_spawn", default=(0, 0)):
        """World-pixel position of the first entity marker matching `kind`
        (e.g. the "player_spawn" placed in the editor). Falls back to
        `default` if the level has no such marker."""
        entities = self.tilemap.get_entities(kind)
        pos = entities[0]["pos"] if entities else default
        return pygame.Vector2(pos)

    def _draw_order(self):
        """Layer ids back-to-front. Falls back to a sorted scan if the file
        didn't carry layer_order (e.g. the legacy flat-list format)."""
        if self.tilemap.layer_order:
            return self.tilemap.layer_order
        seen = set()
        for bucket in self.tilemap.chunks.values():
            for raw in bucket:
                seen.add(raw.get("layer", 0))
        return sorted(seen)

    def draw(self, surface, camera_rect, camera_offset=None, include_hidden=False, exclude_layers=None):
        """Draws every visible layer, back to front, clipped to camera_rect.
        camera_offset defaults to camera_rect's own top-left, which is the
        common case (camera_rect IS the view). Pass it explicitly if your
        Camera does screen-shake or other offsetting on top of the view rect.
        exclude_layers skips given layer ids entirely - for layers your game
        code is handling itself instead of letting this draw them statically
        (e.g. tiles you've turned into your own animated/interactive objects)."""
        offset = camera_offset if camera_offset is not None else (camera_rect.x, camera_rect.y)
        exclude_layers = exclude_layers or ()
        for layer in self._draw_order():
            if layer in exclude_layers:
                continue
            for entry in self.tilemap.get_visible_tiles(camera_rect, layer=layer, include_hidden=include_hidden):
                if entry.tileset in self.tilemap.hidden_tilesets:
                    continue
                surface.blit(entry.get_surface(), (entry.rect.x - offset[0], entry.rect.y - offset[1]))

    def get_solid_rects(self, camera_rect, layers=None):
        """AABB rects for collision, from self.solid_layers (or an override).
        Excludes ramp tiles (see get_ramps) - those need slope resolution,
        not flat AABB blocking, so treating them as regular solids too would
        make movement code fight itself over the same tile.
        Only queries tiles near camera_rect - fine for jam-sized levels where
        the player is always roughly on-screen; if you need off-screen
        physics (e.g. falling objects far from the camera), widen camera_rect
        before calling, or query the full level with tilemap.iter_all_tiles()."""
        layers = layers if layers is not None else self.solid_layers
        rects = []
        for layer in layers:
            for entry in self.tilemap.get_visible_tiles(camera_rect, layer=layer):
                if not entry.ramp and entry.tileset not in self.tilemap.nonsolid_tilesets:
                    rects.append(entry.rect)
        return rects

    def get_ramps(self, camera_rect, layers=None):
        """TileEntry objects with a nonzero .ramp (1 = up-right, 2 = up-left)
        so your movement code can do slope resolution separately from flat
        AABB collision."""
        layers = layers if layers is not None else self.solid_layers
        result = []
        for layer in layers:
            for entry in self.tilemap.get_visible_tiles(camera_rect, layer=layer):
                if entry.ramp:
                    result.append(entry)
        return result

    @property
    def tile_size(self):
        return self.tilemap.tile_size