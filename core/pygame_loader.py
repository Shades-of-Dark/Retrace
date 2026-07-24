"""Standalone reader for levels saved by the framework level editor.

    from pygame_loader import TileMap

    level = TileMap.load("levels/mylevel.json", tilesets_dir="tilesets")

    camera_rect = pygame.Rect(camera_x, camera_y, screen_w, screen_h)
    for entry in level.get_visible_tiles(camera_rect, layer=0):
        screen.blit(entry.get_surface(), (entry.rect.x - camera_x, entry.rect.y - camera_y))

    if entry.ramp:
        ...  # 1 = ramp up-right, 2 = ramp up-left (matches tile.py's convention)

screen_w/screen_h above are YOUR game's own resolution, not the editor's -
get_visible_tiles() only does rect-overlap math against whatever camera_rect
you pass it, so it works the same at any screen size; chunk lookups are
bounded by camera_rect's extent, not by the editor's own window.

Layers hidden in the editor's layers panel are skipped by default (pass
include_hidden=True to see everything anyway, e.g. for a debug layer).

Which layers are solid is data, not something the game hardcodes: the
editor's per-layer "solid" toggle round-trips as top-level "layer_collision"
in the JSON, exposed here as `tilemap.solid_layers` (a set of layer ids) and
`tilemap.is_layer_solid(layer_id)`.

Entity markers (e.g. a player_spawn placed in the editor) show up in
`tilemap.entities` / `tilemap.get_entities(kind=...)`, with `pos` already
converted to world pixels.

Coordinate model: an entry's grid position (`pos`) is in the level's
canonical tile_size (top-level "tile_size" in the JSON) - that's what decides
WHERE it sits. Its rendered size comes from its own tileset's tile_size *
scale - that's what decides how BIG it draws. If a tileset's scale doesn't
match the canonical tile_size, tiles from it will overhang/underhang their
grid cell, which is intentional (e.g. a tall prop drawn bigger than its
single-cell footprint) rather than a bug.
"""
import os
import json
import pygame


def _clip(surf, x, y, w, h):
    handle_surf = surf.copy()
    clip_rect = pygame.Rect(x, y, w, h)
    handle_surf.set_clip(clip_rect)
    return surf.subsurface(handle_surf.get_clip()).copy()


class TileEntry:
    __slots__ = ("rect", "surface", "layer", "x_flip", "y_flip", "is_asset", "ramp", "pos", "tileset","props", "_flipped")

    def __init__(self, rect, surface, layer, x_flip, y_flip, is_asset, ramp, pos, tileset, props=None):
        self.rect = rect
        self.surface = surface
        self.layer = layer
        self.x_flip = x_flip
        self.y_flip = y_flip
        self.is_asset = is_asset
        self.ramp = ramp
        self.pos = pos
        self.tileset = tileset
        self._flipped = None
        self.props = props or {}

    def get_surface(self):
        """Surface already flipped per x_flip/y_flip, ready to blit at rect.topleft."""
        if not self.x_flip and not self.y_flip:
            return self.surface
        if self._flipped is None:
            self._flipped = pygame.transform.flip(self.surface, self.x_flip, self.y_flip)
        return self._flipped


class _TilesetSource:
    def __init__(self, name, tilesets_dir):
        self.name = name
        image_path = os.path.join(tilesets_dir, f"{name}.png")
        config_path = os.path.join(tilesets_dir, f"{name}.json")
        self.tile_size = 16
        self.scale = 1.0
        if os.path.isfile(config_path):
            with open(config_path) as f:
                cfg = json.load(f)
            self.tile_size = int(cfg.get("tile_size", 16))
            self.scale = float(cfg.get("scale", 1.0))
        image = pygame.image.load(image_path).convert()
        image.set_colorkey((0, 0, 0))
        self.cols = max(1, image.get_width() // self.tile_size)
        self.rows = max(1, image.get_height() // self.tile_size)
        self._raw_tiles = {}
        self._scaled_tiles = {}
        self._block_cache = {}
        self.tile_props = {int(k): v for k, v in cfg.get("tile_props", {}).items()}
        idx = 0
        for y in range(self.rows):
            for x in range(self.cols):
                raw = _clip(image, x * self.tile_size, y * self.tile_size, self.tile_size, self.tile_size)
                self._raw_tiles[idx] = raw
                self._scaled_tiles[idx] = self._scale_surface(raw)
                idx += 1

    def _scale_surface(self, surf):
        if self.scale == 1.0:
            return surf
        w = max(1, round(surf.get_width() * self.scale))
        h = max(1, round(surf.get_height() * self.scale))
        return pygame.transform.scale(surf, (w, h))

    def tile_surface(self, index):
        return self._scaled_tiles.get(index)

    def block_surface(self, origin, w, h):
        key = (origin[0], origin[1], w, h)
        if key in self._block_cache:
            return self._block_cache[key]
        ox, oy = origin
        block = pygame.Surface((w * self.tile_size, h * self.tile_size))
        block.set_colorkey((0, 0, 0))
        for ry in range(h):
            for rx in range(w):
                idx = (oy + ry) * self.cols + (ox + rx)
                tile_img = self._raw_tiles.get(idx)
                if tile_img is not None:
                    block.blit(tile_img, (rx * self.tile_size, ry * self.tile_size))
        surf = self._scale_surface(block)
        self._block_cache[key] = surf
        return surf


def _load_asset_defs(tilesets_dir):
    path = os.path.join(tilesets_dir, "assets.json")
    defs = {}
    if os.path.isfile(path):
        with open(path) as f:
            data = json.load(f)
        for d in data:
            defs[d["id"]] = d
    return defs


class TileMap:
    def __init__(self, tile_size, chunk_size, tilesets, asset_defs, chunks,
                 layer_order=None, layer_visible=None, layer_names=None,
                 layer_collision=None, entities=None):
        self.tile_size = tile_size
        self.chunk_size = chunk_size
        self.tilesets = tilesets      # name -> _TilesetSource
        self.asset_defs = asset_defs  # id -> {"tileset", "origin", "w", "h", "ramp"}
        self.chunks = chunks          # (cx, cy) -> list[raw entry dict]
        self.layer_order = layer_order or []      # editor's back-to-front layer order
        self.layer_visible = layer_visible or {}  # layer id -> bool (hidden-in-editor layers,
                                                   # e.g. debug/annotation layers, default visible)
        self.layer_names = layer_names or {}
        self.layer_collision = layer_collision or {}  # layer id -> bool, set by the editor's
                                                        # per-layer "solid" toggle
        self.entities = entities or []  # [{"kind", "pos" (world px), "layer"}]
        # Tileset names pulled out of the generic draw/solids pipeline by
        # remove_from_draw()/remove_from_solids() - e.g. water, which
        # game/water.py renders and collides with on its own terms. Each is
        # independent: a tileset can be undrawn but still solid, or vice
        # versa. Raw entries are untouched in self.chunks either way, so
        # code that reads chunks directly (water's flood fill) still sees
        # them regardless of these sets.
        self.hidden_tilesets = set()
        self.nonsolid_tilesets = set()

    def remove_from_draw(self, tileset_name):
        """Tiles from this tileset stop appearing in draw() (via
        get_visible_tiles' TileEntry.tileset), no matter their layer."""
        self.hidden_tilesets.add(tileset_name)

    def restore_to_draw(self, tileset_name):
        self.hidden_tilesets.discard(tileset_name)

    def remove_from_solids(self, tileset_name):
        """Tiles from this tileset stop appearing in get_solid_rects(),
        no matter their layer."""
        self.nonsolid_tilesets.add(tileset_name)

    def restore_to_solids(self, tileset_name):
        self.nonsolid_tilesets.discard(tileset_name)

    @classmethod
    def load(cls, level_path, tilesets_dir="tilesets"):
        with open(level_path) as f:
            data = json.load(f)

        if isinstance(data, list):
            # Legacy flat-list format (pre-chunking). Best-effort load: bucket
            # by the default chunk size using whatever "pos" units the file
            # already used.
            tile_size = 16
            chunk_size = 16
            raw_entries = data
            layer_order, layer_visible, layer_names, layer_collision = [], {}, {}, {}
        else:
            tile_size = data.get("tile_size", 16)
            chunk_size = data.get("chunk_size", 16)
            raw_entries = [entry for bucket in data.get("chunks", {}).values() for entry in bucket]
            layer_order = list(data.get("layer_order", []))
            layer_visible = {int(k): v for k, v in data.get("layer_visible", {}).items()}
            layer_names = {int(k): v for k, v in data.get("layer_names", {}).items()}
            layer_collision = {int(k): v for k, v in data.get("layer_collision", {}).items()}

        asset_defs = _load_asset_defs(tilesets_dir)

        tileset_names = {e.get("tileset") for e in raw_entries if e.get("tileset")}
        tileset_names |= {d.get("tileset") for d in asset_defs.values() if d.get("tileset")}
        tilesets = {}
        for name in tileset_names:
            if not name:
                continue
            try:
                tilesets[name] = _TilesetSource(name, tilesets_dir)
            except (FileNotFoundError, pygame.error):
                continue

        chunks = {}
        entities = []
        for entry in raw_entries:
            pos = entry["pos"]
            # int(): off-grid (foliage-style) entries have fractional
            # positions - floor-dividing a float yields a float chunk index,
            # which would break dict-key consistency with the int chunk
            # coords _chunk_coord() produces from integer camera-space math.
            key = (int(pos[0] // chunk_size), int(pos[1] // chunk_size))
            chunks.setdefault(key, []).append(entry)
            if entry.get("type") == "entity":
                entities.append({
                    "kind": entry.get("kind"),
                    "pos": (pos[0] * tile_size, pos[1] * tile_size),
                    "layer": entry.get("layer", 0),
                })

        return cls(tile_size, chunk_size, tilesets, asset_defs, chunks,
                  layer_order, layer_visible, layer_names, layer_collision, entities)

    def _chunk_coord(self, tx, ty):
        return (int(tx // self.chunk_size), int(ty // self.chunk_size))

    def is_layer_visible(self, layer_id):
        return self.layer_visible.get(layer_id, True)

    def is_layer_solid(self, layer_id):
        return self.layer_collision.get(layer_id, False)

    @property
    def solid_layers(self):
        """Layer ids flagged as collidable in the level file itself (the
        editor's per-layer "solid" toggle) - read from the data instead of
        needing the game to hardcode which layer ids are solid."""
        return {layer_id for layer_id, solid in self.layer_collision.items() if solid}

    def get_entities(self, kind=None):
        """Entity markers placed in the editor (e.g. player_spawn). pos is
        already in world pixels, unlike the raw entry's tile-grid pos."""
        if kind is None:
            return list(self.entities)
        return [e for e in self.entities if e["kind"] == kind]

    def _make_entry(self, raw):
        etype = raw.get("type", "tile")
        pos = raw["pos"]
        world_x = pos[0] * self.tile_size
        world_y = pos[1] * self.tile_size

        if etype == "asset":
            asset_def = self.asset_defs.get(raw.get("asset"))
            if asset_def is None:
                return None
            tileset_name = asset_def.get("tileset")
            tileset = self.tilesets.get(tileset_name)
            if tileset is None:
                return None
            surf = tileset.block_surface(asset_def["origin"], asset_def.get("w", 1), asset_def.get("h", 1))
            ramp = asset_def.get("ramp", 0)
            props = asset_def.get("props", {})
        else:
            tileset_name = raw.get("tileset")
            tileset = self.tilesets.get(tileset_name)
            if tileset is None:
                return None
            surf = tileset.tile_surface(raw.get("tile", 0))
            ramp = 0

            tile_index = raw.get("tile", 0)
            props = tileset.tile_props.get(tile_index, {})

        if surf is None:
            return None

        rect = pygame.Rect(world_x, world_y, surf.get_width(), surf.get_height())
        return TileEntry(rect, surf, raw.get("layer", 0), bool(raw.get("x_flip", False)),
                         bool(raw.get("y_flip", False)), etype == "asset", ramp, tuple(pos), tileset_name, props)

    def iter_all_tiles(self, layer=None, include_hidden=False):
        for bucket in self.chunks.values():
            for raw in bucket:
                raw_layer = raw.get("layer", 0)
                if layer is not None and raw_layer != layer:
                    continue
                if not include_hidden and not self.is_layer_visible(raw_layer):
                    continue
                entry = self._make_entry(raw)
                if entry is not None:
                    yield entry

    def get_visible_tiles(self, camera_rect, layer=None, margin_tiles=2, include_hidden=False):
        """Tiles/assets whose rect overlaps camera_rect (an arbitrary
        world-pixel-space pygame.Rect - pass your own game's actual camera
        view, any width/height; this makes no assumption about screen size).
        margin_tiles pads the chunk lookup so assets whose origin sits just
        outside the camera but bleed into it are still included. Layers
        hidden in the editor are skipped by default (include_hidden=True to
        see everything regardless, e.g. for a debug/annotation layer)."""
        t0x = camera_rect.left // self.tile_size - margin_tiles
        t0y = camera_rect.top // self.tile_size - margin_tiles
        t1x = camera_rect.right // self.tile_size + margin_tiles
        t1y = camera_rect.bottom // self.tile_size + margin_tiles
        min_cx, min_cy = self._chunk_coord(t0x, t0y)
        max_cx, max_cy = self._chunk_coord(t1x, t1y)

        seen_ids = set()
        result = []
        for ccx in range(min_cx, max_cx + 1):
            for ccy in range(min_cy, max_cy + 1):
                for raw in self.chunks.get((ccx, ccy), ()):
                    raw_layer = raw.get("layer", 0)
                    if layer is not None and raw_layer != layer:
                        continue
                    if not include_hidden and not self.is_layer_visible(raw_layer):
                        continue
                    if id(raw) in seen_ids:
                        continue
                    entry = self._make_entry(raw)
                    if entry is None:
                        continue
                    if entry.rect.colliderect(camera_rect):
                        seen_ids.add(id(raw))
                        result.append(entry)
        return result

    def get_chunk_coords_in_rect(self, rect):
        t0x, t0y = rect.left // self.tile_size, rect.top // self.tile_size
        t1x, t1y = rect.right // self.tile_size, rect.bottom // self.tile_size
        min_cx, min_cy = self._chunk_coord(t0x, t0y)
        max_cx, max_cy = self._chunk_coord(t1x, t1y)
        return [(cx, cy) for cx in range(min_cx, max_cx + 1) for cy in range(min_cy, max_cy + 1)]
