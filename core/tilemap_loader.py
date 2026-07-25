
import pygame

from core.pygame_loader import TileMap


class Level:


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

        entities = self.tilemap.get_entities(kind)
        pos = entities[0]["pos"] if entities else default
        return pygame.Vector2(pos)

    def find_asset_rect(self, asset_id):

        ts = self.tilemap.tile_size
        for bucket in self.tilemap.chunks.values():
            for raw in bucket:
                if raw.get("type") == "asset" and raw.get("asset") == asset_id:
                    x, y = raw["pos"]
                    w, h = raw.get("w", 1), raw.get("h", 1)
                    return pygame.Rect(round(x * ts), round(y * ts), w * ts, h * ts)
        return None

    def _draw_order(self):

        if self.tilemap.layer_order:
            return self.tilemap.layer_order
        seen = set()
        for bucket in self.tilemap.chunks.values():
            for raw in bucket:
                seen.add(raw.get("layer", 0))
        return sorted(seen)

    def draw(self, surface, camera_rect, camera_offset=None, include_hidden=False, exclude_layers=None):

        offset = camera_offset if camera_offset is not None else (camera_rect.x, camera_rect.y)
        exclude_layers = exclude_layers or ()
        for layer in self._draw_order():
            if layer in exclude_layers:
                continue
            for entry in self.tilemap.get_visible_tiles(camera_rect, layer=layer, include_hidden=include_hidden):
                if entry.tileset in self.tilemap.hidden_tilesets:
                    continue
                if self.tilemap.is_prop_hidden(entry.props):
                    continue
                surface.blit(entry.get_surface(), (entry.rect.x - offset[0], entry.rect.y - offset[1]))

    def get_marker_rect(self, key, value=None):

        for entry in self.tilemap.iter_all_tiles(include_hidden=True):
            if key in entry.props and (value is None or entry.props[key] == value):
                return entry.rect
        return None

    def get_marker_entry(self, key, value=None):

        for entry in self.tilemap.iter_all_tiles(include_hidden=True):
            if key in entry.props and (value is None or entry.props[key] == value):
                return entry
        return None

    def get_solid_rects(self, camera_rect, layers=None):

        layers = layers if layers is not None else self.solid_layers
        rects = []
        for layer in layers:
            for entry in self.tilemap.get_visible_tiles(camera_rect, layer=layer):
                if not entry.ramp and entry.tileset not in self.tilemap.nonsolid_tilesets:
                    rects.append(entry.rect)
        return rects

    def get_ramps(self, camera_rect, layers=None):

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
