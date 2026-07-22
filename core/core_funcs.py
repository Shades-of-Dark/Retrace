import pygame
import numpy as np


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
