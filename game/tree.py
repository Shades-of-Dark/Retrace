import math
import random
import pygame
import numpy as np
from core.core_funcs import cut_surface, make_alpha_mask


def _clamp(value, lo, hi):
    return max(lo, min(hi, value))


class Tree:
    SWAY_AMPLITUDE = 2  # idle sway, px
    SWAY_SPEED = 1.0  # base oscillation rate, radians/sec, before wind

    WIND_REFERENCE_SPEED = 120  # px/s - roughly the middle of WindField's default speed_range;
    # wind_norm=1.0 means "a typical gust," not the max possible
    WIND_MAX_OFFSET = 2  # cap so a strong gust can't fling chunks off
    WIND_EASE_RATE = 3.0
    WIND_INFLUENCE = 0.15  # px of offset per (px/s) of wind speed
    WIND_SWAY_SPEED_MULT = 1.5  # at wind_norm=1, sway oscillates 2.5x as fast
    WIND_SWAY_AMP_MULT = 0.6  # at wind_norm=1, sway swings 60% wider too

    LEAF_MAX_COUNT = 50
    LEAF_SPAWN_CHANCE = 0.02  # base per-frame chance, calm conditions
    WIND_LEAF_SPAWN_MULT = 4.0  # at wind_norm=1, spawn chance is 5x base
    LEAF_FALL_SPEED = 20  # px/s downward

    LEAF_BASE_DRIFT_RANGE = (-25, -8)  # baseline leftward speed, px/s, before wind -
    # this is what keeps leaves moving even with zero wind
    LEAF_WAVE_AMPLITUDE = 18
    LEAF_WAVE_FREQ = 1.2

    LEAF_LIFETIME = 10.0

    def __init__(self, mask, tree_img, pos, targets, leave_imgs):
        self.mask = make_alpha_mask(mask)
        self.tree_img = tree_img

        self.pos = pos
        self.rect = self.tree_img.get_rect(topleft=pos)
        self.leaves = []
        self.leaf_imgs = leave_imgs
        rgb = pygame.surfarray.array3d(targets)
        target_color = (255, 0, 0)
        check = np.all(rgb == target_color, axis=-1)
        xs, ys = np.where(check)
        self.target_poses = list(zip(xs, ys))

        mask_w, mask_h = self.mask.get_size()
        self.mask_half = (mask_w // 2, mask_h // 2)

        self.base_image = self.tree_img.copy()

        self.chunks = []
        for (tx, ty) in self.target_poses:
            topleft = (tx - self.mask_half[0], ty - self.mask_half[1])

            raw_chunk = cut_surface(self.tree_img, topleft[0], topleft[1], mask_w, mask_h)
            shaped_chunk = raw_chunk.copy()
            shaped_chunk.blit(self.mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

            self.chunks.append({
                "surface": shaped_chunk,
                "base_topleft": topleft,
                "phase": random.uniform(0, math.tau),
                "sway_phase": random.uniform(0, math.tau),  # accumulates at a variable rate now,
                # so it has to be its own running value,
                # not derived from self.time directly
                "wind_offset": 0.0,
            })

        self.image = self.base_image.copy()
        self.time = 0.0

    def _wind_norm(self, wind):
        """0 = calm, 1 = a typical gust, can exceed 1 for a strong one."""
        if wind is None:
            return 0.0
        center_x = self.pos[0] + self.mask_half[0]
        return abs(wind.speed_at(center_x)) / self.WIND_REFERENCE_SPEED

    def update(self, dt, wind=None, camera_rect=None):
        self.time += dt
        self.image = self.base_image.copy()

        wind_norm = self._wind_norm(wind)

        # --- spawn rate scales with wind ---
        effective_spawn_chance = self.LEAF_SPAWN_CHANCE * (1 + wind_norm * self.WIND_LEAF_SPAWN_MULT)
        if len(self.leaves) < self.LEAF_MAX_COUNT and random.random() < effective_spawn_chance:
            spawn_x = self.pos[0] + random.randint(0, self.rect.width)
            spawn_y = self.pos[1] + random.randint(0, self.rect.height // 4)
            self.leaves.append({
                "img": random.choice(self.leaf_imgs),
                "pos": [float(spawn_x), float(spawn_y)],
                "base_drift": random.uniform(*self.LEAF_BASE_DRIFT_RANGE),  # baseline motion, wind-independent
                "age": 0.0,
            })

        for leaf in self.leaves:
            leaf["age"] += dt

            wind_speed = wind.speed_at(leaf["pos"][0]) if wind is not None else 0.0
            flutter_x = math.sin(leaf["age"] * self.LEAF_WAVE_FREQ) * self.LEAF_WAVE_AMPLITUDE
            flutter_y = math.cos(leaf["age"] * self.LEAF_WAVE_FREQ * 0.6) * self.LEAF_WAVE_AMPLITUDE * 0.3

            # base_drift always applies; wind_speed adds on top (both
            # negative = leftward, so wind speeds up the same direction
            # rather than fighting it)
            leaf["pos"][0] += (leaf["base_drift"] + wind_speed + flutter_x) * dt
            leaf["pos"][1] += self.LEAF_FALL_SPEED * dt + flutter_y * dt

        if camera_rect is not None:
            bounds = camera_rect.inflate(64, 64)
            self.leaves = [
                leaf for leaf in self.leaves
                if bounds.collidepoint(leaf["pos"]) and leaf["age"] < self.LEAF_LIFETIME
            ]
        else:
            self.leaves = [leaf for leaf in self.leaves if leaf["age"] < self.LEAF_LIFETIME]

        # --- tree sway rate + amplitude scale with wind ---
        effective_sway_speed = self.SWAY_SPEED * (1 + wind_norm * self.WIND_SWAY_SPEED_MULT)
        effective_sway_amp = self.SWAY_AMPLITUDE * (1 + wind_norm * self.WIND_SWAY_AMP_MULT)

        for chunk in self.chunks:
            chunk["sway_phase"] += effective_sway_speed * dt
            idle_sway = math.sin(chunk["sway_phase"] + chunk["phase"]) * effective_sway_amp

            if wind is not None:
                world_x = self.pos[0] + chunk["base_topleft"][0] + self.mask_half[0]
                chunk_wind_speed = wind.speed_at(world_x)
                target = _clamp(chunk_wind_speed * self.WIND_INFLUENCE, -self.WIND_MAX_OFFSET, self.WIND_MAX_OFFSET)
            else:
                target = 0.0

            t = min(1.0, self.WIND_EASE_RATE * dt)
            chunk["wind_offset"] += (target - chunk["wind_offset"]) * t

            total_x = idle_sway + chunk["wind_offset"]
            total_y = idle_sway * 0.3 + (chunk["wind_offset"] * 0.4)

            offset = (
                chunk["base_topleft"][0] + int(total_x),
                chunk["base_topleft"][1] + int(total_y),
            )
            self.image.blit(chunk["surface"], offset)

    def draw(self, surface, camera=None):
        rect = camera.apply(self.rect) if camera else self.rect
        surface.blit(self.image, rect)
        for leaf in self.leaves:
            pos = camera.apply_pos(leaf["pos"]) if camera else leaf["pos"]
            surface.blit(leaf["img"], pos)
