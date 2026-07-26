import os

import pygame

from ..core_funcs import resource_path
from ..pixelfont import Font as _FontAtlas

DEFAULT_FONT_PATH = resource_path(os.path.join("core", "ui_assets", "font.png"))

# Atlases are re-parsed from the PNG on first use per path, then shared
# across every PixelFont instance at any scale/color/outline combination.
_atlas_cache = {}


def _get_atlas(path):
    atlas = _atlas_cache.get(path)
    if atlas is None:
        atlas = _FontAtlas(path)
        _atlas_cache[path] = atlas
    return atlas


class PixelFont:
    """pygame.font.Font-compatible wrapper around the bitmap font atlas in
    core/pixelfont.py, so it drops into any core/ui widget or core/states
    title in place of pygame.font.SysFont - same .render()/.size() calls,
    pixel art glyphs instead of a system font."""

    def __init__(self, path=DEFAULT_FONT_PATH, scale=2, outline_color=(0, 0, 0), outline=True):
        self._atlas = _get_atlas(path)
        self.scale = scale
        self.outline_color = outline_color
        self.outline = outline
        self._glyph_height = next(iter(self._atlas.characters.values())).get_height()

    def size(self, text):
        return (round(self._atlas.get_width(text, self.scale)), self.get_height())

    def get_height(self):
        return self._glyph_height * self.scale

    def render(self, text, antialias=True, color=(255, 255, 255), background=None):
        width, height = self.size(text)
        surf = pygame.Surface((max(1, width), height), pygame.SRCALPHA)
        if background is not None:
            surf.fill(background)
        self._atlas.render(surf, text, color, (0, 0), self.scale, self.outline_color, outline=self.outline)
        return surf
