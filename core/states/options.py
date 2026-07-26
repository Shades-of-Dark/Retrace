import pygame

from ..state_manager import GameState
from ..ui import DEFAULT_THEME, Button, Checkbox, Label, Panel, PixelFont, Slider, UIManager, ui_scale


def _surface_size():
    surface = pygame.display.get_surface()
    return surface.get_size() if surface else (960, 540)


class OptionsState(GameState):
    """Audio options overlay - music/SFX volume sliders and a mute
    checkbox, wired straight to an AudioManager. Generic: push it on top
    of a menu, a pause screen, or anything else; Back/Escape pops it."""

    def __init__(self, manager, audio_manager, theme=None, size=None):
        super().__init__(manager)
        self.audio = audio_manager
        self.theme = theme or DEFAULT_THEME
        self.size = size
        scale = ui_scale((self.size or _surface_size())[0])
        self.title_font = PixelFont(scale=max(1, round(3 * scale)))
        self.ui = UIManager()
        self._build_ui(scale)

    def _build_ui(self, scale):
        width, height = self.size or _surface_size()
        panel_width, panel_height = round(360 * scale), round(240 * scale)
        panel_rect = (
            width // 2 - panel_width // 2,
            height // 2 - panel_height // 2,
            panel_width,
            panel_height,
        )
        panel = self.ui.add(Panel(panel_rect, theme=self.theme))
        pad = round(24 * scale)
        left = panel.rect.left + pad
        content_width = panel_width - pad * 2
        font = PixelFont(scale=max(1, round(2 * scale)))

        panel.add(Label((left, panel.rect.top + round(16 * scale)), "Options",
                         font=self.title_font, theme=self.theme))

        panel.add(Label((left, panel.rect.top + round(66 * scale)), "Music volume", font=font, theme=self.theme))
        panel.add(Slider((left, panel.rect.top + round(90 * scale), content_width, round(16 * scale)),
                          0.0, 1.0, value=self.audio.music_volume,
                          on_change=self.audio.set_music_volume, theme=self.theme))

        panel.add(Label((left, panel.rect.top + round(122 * scale)), "SFX volume", font=font, theme=self.theme))
        panel.add(Slider((left, panel.rect.top + round(146 * scale), content_width, round(16 * scale)),
                          0.0, 1.0, value=self.audio.sfx_volume,
                          on_change=self.audio.set_sfx_volume, theme=self.theme))

        checkbox_size = round(20 * scale)
        panel.add(Checkbox((left, panel.rect.top + round(178 * scale), checkbox_size, checkbox_size),
                            checked=self.audio.muted, on_change=self.audio.set_muted,
                            theme=self.theme))
        panel.add(Label((left + round(30 * scale), panel.rect.top + round(178 * scale)), "Mute", font=font, theme=self.theme))

        back_width, back_height = round(100 * scale), round(36 * scale)
        panel.add(Button((panel.rect.right - pad - back_width, panel.rect.bottom - pad - back_height, back_width, back_height),
                          "Back", on_click=self._click(self._back), theme=self.theme, font=font))

    def _click(self, callback):
        def handler():
            self.audio.play("select")
            if callback:
                callback()
        return handler

    def _back(self):
        self.manager.pop()

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._back()
            return
        self.ui.handle_event(event)

    def update(self, dt):
        self.ui.update(dt)

    def draw(self, surface):
        # Dim whatever state is beneath this one in the stack, then draw
        # the panel on top of it.
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        surface.blit(overlay, (0, 0))
        self.ui.draw(surface)
