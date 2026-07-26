import os
import sys

import pygame
import pygame.surfarray as surfarray
import numpy as np


def resource_path(relative_path):
    """Get path to a resource, works for dev and for PyInstaller onefile exe."""
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, relative_path)


def palette_swap(surf, old_c, new_c):
    surfCopy = surf.copy()  # colorkey carries over from surf automatically
    pixels = pygame.PixelArray(surfCopy)
    pixels.replace(old_c, new_c)
    del pixels  # unlock the surface
    return surfCopy


def file_read(path):
    with open(path, "r") as f:
        contents = f.read()
    return contents


def file_write(contents, path):
    with open(path, "w") as f:
        f.write(contents)


def cut_surface(surf, x, y, w, h):
    new_clipped_surface = pygame.Surface((w, h), pygame.SRCALPHA)
    source_area = pygame.Rect(x, y, w, h)
    new_clipped_surface.blit(surf, (0, 0), source_area)
    return new_clipped_surface


def circle_surf(radius, color):
    surf = pygame.Surface((radius * 2, radius * 2))
    pygame.Surface.set_colorkey(surf, (0, 0, 0))
    pygame.draw.circle(surf, color, (radius, radius), radius)
    surf.set_alpha(50)
    return surf


def get_image(sheet, frame, width, height, color, xoffset=0, yoffset=0, scale=0, scale2=(0, 0)):
    image = pygame.Surface((width, height)).convert()
    image.blit(sheet, (0, 0), area=(frame * width + xoffset, 0 + yoffset, width, height))
    if scale2 != (0, 0):
        image = pygame.transform.scale(image, scale2)
    elif scale != 0:
        image = pygame.transform.scale(image, (scale, scale))
    # else: leave it at its native width x height
    pygame.Surface.set_colorkey(image, color)
    return image

def to_alpha_surface(surface):
    """Convert to a true per-pixel-alpha surface, mapping any existing
    colorkey to alpha=0. Plain .convert_alpha() doesn't know about
    colorkey transparency - it leaves those pixels opaque, which is why
    colorkeyed sprites (most of this game's tile/item art) came out with
    a solid black box where the "transparent" background used to be."""
    colorkey = surface.get_colorkey()
    out = surface.convert_alpha()
    if colorkey is not None:
        rgb = surfarray.pixels3d(out)
        alpha = surfarray.pixels_alpha(out)
        key = np.array(colorkey[:3])
        alpha[np.all(rgb == key, axis=-1)] = 0
        del rgb, alpha
    return out


def desaturate_surface(surface, amount=0.5):
    """Blend toward grayscale by `amount` (0-1). The single dim/gray
    implementation shared by the whole-room desaturation effect and the
    per-item "already checked" treatment - goes through to_alpha_surface
    so it's equally correct on an opaque screen capture or a
    colorkey-transparent sprite."""
    out = to_alpha_surface(surface)
    arr = surfarray.pixels3d(out)
    gray = arr[..., 0] * 0.299 + arr[..., 1] * 0.587 + arr[..., 2] * 0.114
    for c in range(3):
        arr[..., c] = (arr[..., c] * (1 - amount) + gray * amount).astype(arr.dtype)
    del arr
    return out


def additive_glow(image, color, amount):
    """Adds `color` scaled by `amount` on top of image via BLEND_RGB_ADD -
    additive light instead of interpolating toward a flat color, so it
    reads as lighting up rather than fading (blending toward white
    desaturates a sprite the same way blending toward gray does, just
    lighter - not the effect we want for "correct" vs "wrong"). Uses
    BLEND_RGB_ADD rather than BLEND_RGBA_ADD deliberately: it leaves alpha
    untouched, so `image` must already be a true per-pixel-alpha surface
    (see to_alpha_surface) - if it were colorkey-transparent instead, the
    background's RGB would drift off the key color and stop being
    recognized as transparent."""
    glow_layer = pygame.Surface(image.get_size(), pygame.SRCALPHA)
    r, g, b = color
    glow_layer.fill((round(r * amount), round(g * amount), round(b * amount), 0))

    result = image.copy()
    result.blit(glow_layer, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
    return result


def make_alpha_mask(mask_surf):
    """Black-background/white-shape mask -> true alpha mask.
    White pixels become alpha 255 (kept), black become alpha 0 (transparent).
    Run this once at load time, not per frame."""
    mask_surf = mask_surf.convert_alpha()
    rgb = pygame.surfarray.pixels3d(mask_surf)
    alpha = pygame.surfarray.pixels_alpha(mask_surf)

    is_white = np.all(rgb > 200, axis=-1)  # tolerant threshold, not exact (255,255,255)
    alpha[:] = np.where(is_white, 255, 0)

    del rgb, alpha  # release the surface locks before using mask_surf again
    return mask_surf
