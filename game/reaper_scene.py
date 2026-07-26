import math
import random

import pygame

from core.animation import slice_spritesheet
from core.core_funcs import resource_path
from core.particles import ParticleSystem
from core.state_manager import GameState
from core.ui.pixel_font import PixelFont

REAPER_SHEET_PATH = resource_path("game/assets/images/reaper/reaper.png")
REAPER_FRAME_SIZE = (128, 128)
REAPER_TOP_MARGIN = 5

IDLE_FRAME_DURATION = 0.35
BOB_AMPLITUDE = 2
BOB_SPEED = 2.2

MIN_LINE_DISPLAY_TIME = 0.4

INTRO_HOLD_DURATION = 0.6   # pure black beat before anything appears -
                            # the "this run is different" signal, since
                            # nothing else marks this as the last one
INTRO_FADE_DURATION = 0.8   # then the reaper fades in out of that hold

BG_COLOR = (10, 10, 14)
TEXT_COLOR = (235, 230, 220)
TEXT_MARGIN = 24
TEXT_LINE_GAP = 3
TEXT_BOTTOM_OFFSET = 22
TEXT_SCALE = 1

ENDING_LINE = "Some things you can't outrun. Only reach for."
ENDING_WORDMARK = "Retrace"
ENDING_CREDITS = "Thanks for playing. - Shades-of-Dark"
ENDING_FADE_DURATION = 1.5
ENDING_LINE_FADE = 0.8
ENDING_WORDMARK_DELAY = 1.2
ENDING_WORDMARK_FADE = 0.6
ENDING_CREDITS_DELAY = 0.4
ENDING_CREDITS_FADE = 0.6
ENDING_CREDITS_COLOR = (200, 195, 185)  # was too dark to read as "fully
                                        # arrived" even at alpha=255
ENDING_HOLD_DURATION = 5.5

REAPER_DUST_PRESET = {
    "count": 1,
    "speed": (2, 5),
    "angle": (0, 360),
    "gravity": 0,
    "color": (190, 185, 180, 45),
    "size": (1, 1),
    "lifetime": (6, 10),
}
REAPER_RED_PRESET = {
    "count": 1,
    "speed": (2, 5),
    "angle": (-100, -80),
    "gravity": -1,
    "color": (140, 25, 20, 55),
    "size": (1, 1),
    "lifetime": (6, 10),
}
REAPER_PARTICLE_INTERVAL = 1.2
REAPER_PARTICLE_PRESPAWN = 6
ENDING_PARTICLE_INTERVAL = 0.6
ENDING_PARTICLE_BURST = 6


REAPER_LINES = [
    "Three times now.",
    "A wheel. A phone. A door you never opened again.",
    "You thought you were fixing things.",
    "You were only ever buying time.",
    "You counted moments. I counted years.",
    "And you still spent every one of them alone.",
    "There's no fourth chance. The count reached zero a long time ago - "
    "I was just being polite about it.",
]


class ReaperScene(GameState):
    def __init__(self, manager, size, on_complete=None):
        super().__init__(manager)
        self.size = size
        self.on_complete = on_complete
        self.lines = []
        self.line_index = 0

        sheet = pygame.image.load(REAPER_SHEET_PATH).convert_alpha()
        self.idle_frames = slice_spritesheet(sheet, *REAPER_FRAME_SIZE)
        self.frame_index = 0
        self.frame_timer = 0.0
        self.bob_time = 0.0
        self.can_advance = False
        self.advance_delay = 0.0


        # "intro" (black hold, then fade the reaper in) -> "dialogue"
        # (player-paced lines) -> "ending" (fade to black, hold on a
        # closing card, then on_complete). Kept as one state rather than
        # separate classes since each phase is just a few extra
        # fields/branches on top of what's already here.
        self.phase = "intro"
        self.intro_timer = 0.0
        self.ending_timer = 0.0
        self._finished = False

        self.font = PixelFont(scale=TEXT_SCALE)
        self.title_font = PixelFont(scale=3)

        self.particles = ParticleSystem()
        self.particles.register_preset("reaper_dust", REAPER_DUST_PRESET)
        self.particles.register_preset("reaper_red", REAPER_RED_PRESET)
        self._particle_timer = 0.0
        self._prespawn_particles()

    def _prespawn_particles(self, count=REAPER_PARTICLE_PRESPAWN):
        w, h = self.size
        for _ in range(count):
            preset = random.choice(("reaper_dust", "reaper_red"))
            pos = (random.uniform(0, w), random.uniform(0, h))
            before = len(self.particles.particles)
            self.particles.emit(preset, pos)
            for p in self.particles.particles[before:]:
                p.age = random.uniform(0, p.lifetime)

    def enter(self, lines=None, **kwargs):
        self.lines = lines if lines is not None else REAPER_LINES
        self.line_index = 0
        self.advance_delay = 0.0
        self.can_advance = False
        self.phase = "intro"
        self.intro_timer = 0.0
        self.ending_timer = 0.0
        self._finished = False

    def _reaper_pos(self, surface):
        w, h = REAPER_FRAME_SIZE
        bob = round(BOB_AMPLITUDE * math.sin(self.bob_time * BOB_SPEED))
        return (surface.get_width() - w) // 2, REAPER_TOP_MARGIN + bob

    def update(self, dt):
        interval = ENDING_PARTICLE_INTERVAL if self.phase == "ending" else REAPER_PARTICLE_INTERVAL
        self._particle_timer += dt
        if self._particle_timer >= interval:
            self._particle_timer -= interval
            w, h = self.size
            preset = random.choice(("reaper_dust", "reaper_red"))
            self.particles.emit(preset, (random.uniform(0, w), random.uniform(0, h)))
        self.particles.update(dt)

        self.bob_time += dt
        self.frame_timer += dt
        if self.frame_timer >= IDLE_FRAME_DURATION:
            self.frame_timer = 0.0
            self.frame_index = (self.frame_index + 1) % len(self.idle_frames)

        if self.phase == "intro":
            self.intro_timer += dt
            if self.intro_timer >= INTRO_HOLD_DURATION + INTRO_FADE_DURATION:
                self.phase = "dialogue"
        elif self.phase == "dialogue":
            self.advance_delay += dt
            self.can_advance = self.advance_delay >= MIN_LINE_DISPLAY_TIME
        elif self.phase == "ending" and not self._finished:
            self.ending_timer += dt
            if self.ending_timer >= ENDING_FADE_DURATION + ENDING_HOLD_DURATION:
                self._finished = True
                if self.on_complete:
                    self.on_complete()

    def handle_event(self, event):
        if self.phase != "dialogue":
            # ending card is a held beat, not a skippable prompt - the
            # point is to give the gut-punch a moment to land before menu
            return
        if self.can_advance and event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            self.line_index += 1
            self.advance_delay = 0.0
            self.can_advance = False
            if self.line_index >= len(self.lines):
                self.phase = "ending"
                self.ending_timer = 0.0
                self._prespawn_particles(ENDING_PARTICLE_BURST)

    def draw(self, surface):
        if self.phase == "intro":
            self._draw_intro(surface)
        elif self.phase == "dialogue":
            self._draw_dialogue(surface)
        else:
            self._draw_ending(surface)

    def _draw_intro(self, surface):
        self._draw_dialogue(surface)
        if self.intro_timer < INTRO_HOLD_DURATION:
            alpha = 255
        else:
            fade_t = min(1.0, (self.intro_timer - INTRO_HOLD_DURATION) / INTRO_FADE_DURATION)
            alpha = round(255 * (1 - fade_t))
        if alpha > 0:
            overlay = pygame.Surface(surface.get_size())
            overlay.fill((0, 0, 0))
            overlay.set_alpha(alpha)
            surface.blit(overlay, (0, 0))

    def _draw_dialogue(self, surface):
        surface.fill(BG_COLOR)
        self.particles.draw(surface)
        surface.blit(self.idle_frames[self.frame_index], self._reaper_pos(surface))
        if self.line_index < len(self.lines):
            self._draw_wrapped_text(surface, self.lines[self.line_index],
                                    surface.get_height() - TEXT_BOTTOM_OFFSET)

    def _draw_ending(self, surface):
        fade_t = min(1.0, self.ending_timer / ENDING_FADE_DURATION)
        if fade_t < 1.0:
            self._draw_dialogue(surface)
            overlay = pygame.Surface(surface.get_size())
            overlay.fill((0, 0, 0))
            overlay.set_alpha(round(255 * fade_t))
            surface.blit(overlay, (0, 0))
            return

        surface.fill((0, 0, 0))
        self.particles.draw(surface)
        card_t = self.ending_timer - ENDING_FADE_DURATION

        line_alpha = round(255 * min(1.0, card_t / ENDING_LINE_FADE))
        if line_alpha > 0:
            self._draw_wrapped_text(surface, ENDING_LINE, surface.get_height() // 2,
                                    color=TEXT_COLOR, alpha=line_alpha)

        wordmark_t = card_t - ENDING_WORDMARK_DELAY
        wordmark_alpha = round(255 * max(0.0, min(1.0, wordmark_t / ENDING_WORDMARK_FADE)))
        if wordmark_alpha > 0:
            wordmark_surf = self.title_font.render(ENDING_WORDMARK, False, (170, 165, 155))
            wordmark_surf.set_alpha(wordmark_alpha)
            surface.blit(wordmark_surf, wordmark_surf.get_rect(
                center=(surface.get_width() // 2, surface.get_height() // 2 + 50)))

        credits_t = wordmark_t - ENDING_WORDMARK_FADE - ENDING_CREDITS_DELAY
        credits_alpha = round(255 * max(0.0, min(1.0, credits_t / ENDING_CREDITS_FADE)))
        if credits_alpha > 0:
            self._draw_wrapped_text(surface, ENDING_CREDITS, surface.get_height() - 18,
                                    color=ENDING_CREDITS_COLOR, alpha=credits_alpha)

    @staticmethod
    def _wrap_text(font, text, max_width):
        words = text.split(" ")
        lines = []
        current = ""
        for word in words:
            candidate = f"{current} {word}" if current else word
            if not current or font.size(candidate)[0] <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    def _draw_wrapped_text(self, surface, text, bottom_y, color=TEXT_COLOR, alpha=None):
        max_width = surface.get_width() - TEXT_MARGIN * 2
        lines = self._wrap_text(self.font, text, max_width)
        line_height = self.font.get_height() + TEXT_LINE_GAP
        top = bottom_y - line_height * len(lines)
        for i, line in enumerate(lines):
            line_surf = self.font.render(line, False, color)
            if alpha is not None:
                line_surf.set_alpha(alpha)
            rect = line_surf.get_rect(midtop=(surface.get_width() // 2, top + i * line_height))
            surface.blit(line_surf, rect)
