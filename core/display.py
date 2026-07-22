import pygame


class VirtualDisplay:
    """Renders everything to a fixed-size virtual surface, then scales that
    single image up (or down) to fill the real window each frame,
    letterboxed to preserve aspect ratio.

    This is the "draw small, scale up" pattern: game and UI code always
    draws against `self.surface` at `virtual_size` and never has to know
    the window's actual size, its aspect ratio, or that it was resized -
    resizing the window just changes how big that one surface ends up on
    screen. It's also why UI layout (menus, panels, buttons) stays
    correctly positioned at any window size without recomputing rects: the
    whole virtual surface, UI included, is one image being scaled.

    virtual_size is typically half or quarter of the window's starting
    size - draw at low-res, scale up, get crisp pixel-art style scaling
    for free with smooth=False (nearest-neighbor, the default).
    """

    def __init__(self, virtual_size, window_size=None, title="", resizable=True, smooth=False):
        self.virtual_size = (int(virtual_size[0]), int(virtual_size[1]))
        flags = pygame.RESIZABLE if resizable else 0
        self.window = pygame.display.set_mode(window_size or self.virtual_size, flags)
        if title:
            pygame.display.set_caption(title)
        self.surface = pygame.Surface(self.virtual_size).convert()
        self.smooth = smooth
        self._scale = 1.0
        self._viewport = pygame.Rect(0, 0, *self.window.get_size())
        self._recalc_viewport()

    def handle_event(self, event):
        """Feed every pygame event through this before your own event
        handling. Keeps the viewport in sync when the window is resized,
        and rewrites mouse positions from window space into virtual space
        in place, so downstream UI/game code never sees window coordinates."""
        if event.type == pygame.VIDEORESIZE:
            self._recalc_viewport()
        elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            event.pos = self.window_to_virtual(event.pos)

    def window_to_virtual(self, pos):
        """Convert a position in real window pixels to virtual-surface
        pixels, clamped to the surface bounds (so dragging a slider past
        the letterbox edge still reads as fully at 0 or max)."""
        x = (pos[0] - self._viewport.x) / self._scale
        y = (pos[1] - self._viewport.y) / self._scale
        vw, vh = self.virtual_size
        return (int(max(0, min(vw - 1, x))), int(max(0, min(vh - 1, y))))

    def _recalc_viewport(self):
        window_w, window_h = self.window.get_size()
        vw, vh = self.virtual_size
        self._scale = max(1e-6, min(window_w / vw, window_h / vh))
        scaled_w, scaled_h = round(vw * self._scale), round(vh * self._scale)
        self._viewport = pygame.Rect(
            (window_w - scaled_w) // 2, (window_h - scaled_h) // 2, scaled_w, scaled_h)

    def present(self):
        """Scale the virtual surface onto the window and flip. Call once
        per frame after everything has drawn onto self.surface."""
        self.window.fill((0, 0, 0))
        scale = pygame.transform.smoothscale if self.smooth else pygame.transform.scale
        self.window.blit(scale(self.surface, self._viewport.size), self._viewport)
        pygame.display.flip()
