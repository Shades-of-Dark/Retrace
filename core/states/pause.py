import pygame

from ..state_manager import GameState
from ..ui import DEFAULT_THEME, Button, Label, Panel, PixelFont, UIManager, ui_scale
from .options import OptionsState


def _surface_size():
    surface = pygame.display.get_surface()
    return surface.get_size() if surface else (960, 540)


class PauseState(GameState):
    """Overlay pushed on top of gameplay. StateManager only updates the
    top of the stack, so pushing this freezes whatever is beneath it;
    StateManager.draw() renders the whole stack, so that frozen frame
    still shows through behind the pause panel.

    on_quit is optional and takes no arguments - if given, it's called
    on "Quit to menu" and is responsible for unwinding the stack itself
    (typically manager.reset(build_menu_state())). Without it, the
    "Quit to menu" button is omitted since core has no menu to return to."""

    def __init__(self, manager, audio_manager, on_quit=None, quit_label="Quit to menu", theme=None, size=None):
        super().__init__(manager)
        self.audio = audio_manager
        self.on_quit = on_quit
        self.quit_label = quit_label
        self.theme = theme or DEFAULT_THEME
        self.size = size
        scale = ui_scale((self.size or _surface_size())[0])
        self.title_font = PixelFont(scale=max(1, round(3 * scale)))
        self.ui = UIManager()
        self._build_ui(scale)

    def _build_ui(self, scale):
        width, height = self.size or _surface_size()
        panel_width = round(280 * scale)
        panel_height = round((220 if self.on_quit else 172) * scale)
        panel_rect = (
            width // 2 - panel_width // 2,
            height // 2 - panel_height // 2,
            panel_width,
            panel_height,
        )
        panel = self.ui.add(Panel(panel_rect, theme=self.theme))
        pad = round(24 * scale)
        left = panel.rect.left + pad
        button_width = panel_width - pad * 2
        button_height = round(40 * scale)
        row_step = round(48 * scale)
        font = PixelFont(scale=max(1, round(2 * scale)))

        panel.add(Label((left, panel.rect.top + round(16 * scale)), "Paused",
                         font=self.title_font, theme=self.theme))

        y = panel.rect.top + round(64 * scale)
        panel.add(Button((left, y, button_width, button_height), "Resume", on_click=self._click(self._resume), theme=self.theme, font=font))
        y += row_step
        panel.add(Button((left, y, button_width, button_height), "Options", on_click=self._click(self._open_options), theme=self.theme, font=font))
        y += row_step
        if self.on_quit:
            panel.add(Button((left, y, button_width, button_height), self.quit_label, on_click=self._click(self.on_quit), theme=self.theme, font=font))

    def _click(self, callback):
        def handler():
            self.audio.play("select")
            if callback:
                callback()
        return handler

    def _resume(self):
        self.manager.pop()

    def _open_options(self):
        self.manager.push(OptionsState(self.manager, self.audio, theme=self.theme, size=self.size))

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._resume()
            return
        self.ui.handle_event(event)

    def update(self, dt):
        self.ui.update(dt)

    def draw(self, surface):
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        surface.blit(overlay, (0, 0))
        self.ui.draw(surface)
