import pygame
import math
from core.state_manager import GameState
from core.tilemap_loader import Level
from core.camera import Camera
from core.ui.pixel_font import PixelFont


class DeathScene(GameState):
    DEFAULT_LEVEL_PATH = "game/assets/levels/death_1.json"
    DEFAULT_TILESETS_DIR = "game/assets/images/tilesets"
    ADVANCE_KEYS = (pygame.K_SPACE, pygame.K_RETURN)
    MIN_DISPLAY_TIME = 1.0

    # How tight the shot is: the camera samples a world-space rect this
    # many times smaller than the actual output size, then that capture
    # gets scaled back up to fill the frame - so the impact point reads as
    # a close, composed moment instead of a small cluster lost in a big
    # empty street.
    ZOOM = 2.75

    # id from assets.json - the car asset placed in the composed scene.
    # Used to find where it actually is so the shadow/skid marks below
    # stay lined up with it even if it gets moved in the editor.

    def __init__(self, manager):
        super().__init__(manager)
        self.level = None
        self.camera = None
        self.size = None
        self.viewport_size = None
        self.next_state = None
        self.time_in_scene = 0.0
        self.car_rect = None

    def _build_impact_fx(self):
        """Builds the shadow + skid mark surfaces once, in world space,
        at enter() time - draw() just blits them with the current camera
        offset subtracted, instead of redrawing every pixel every frame."""
        self._shadow_surf = None
        self._streaks = []
        if self.car_rect is None:
            return
        car = self.car_rect

        # Shadow
        shadow_w, shadow_h = round(car.width * 0.85), 5
        shadow_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, 85), shadow_surf.get_rect())
        self._shadow_surf = shadow_surf
        self._shadow_world_pos = (car.centerx - shadow_w / 2, car.bottom - shadow_h / 2 - 1)

        # Skid marks
        streak_len = 22
        ground_y = car.bottom - 2
        for wheel_x in (car.left + 5, car.left + 27):
            streak = pygame.Surface((streak_len, 2), pygame.SRCALPHA)
            for x in range(streak_len):
                alpha = int(210 * (x / (streak_len - 1)))
                streak.set_at((x, 0), (120, 110, 100, alpha))
                streak.set_at((x, 1), (120, 110, 100, alpha))
            world_pos = (wheel_x - streak_len, ground_y)
            self._streaks.append((streak, world_pos))
    def _blit_impact_fx(self, dest, camera_rect):
        """Just positions the pre-built surfaces relative to the current
        camera offset - no per-frame pixel work."""
        ox, oy = camera_rect.topleft
        if self._shadow_surf is not None:
            wx, wy = self._shadow_world_pos
            dest.blit(self._shadow_surf, (wx - ox, wy - oy))
        for streak, (wx, wy) in self._streaks:
            dest.blit(streak, (wx - ox, wy - oy))
    def enter(self, size=(960, 540), next_state=None, level_path=None, tilesets_dir=None, **kwargs):
        self.size = size
        self.viewport_size = (size[0] / self.ZOOM, size[1] / self.ZOOM)
        self.next_state = next_state
        self.level = Level.load(
            level_path or self.DEFAULT_LEVEL_PATH,
            tilesets_dir=tilesets_dir or self.DEFAULT_TILESETS_DIR,
        )
        self.car_rect = self.level.get_marker_rect("role", "car")
        self.camera = Camera(self.viewport_size[0], self.viewport_size[1], smoothing=0.1)

        # No VERTICAL_BIAS - just center on wherever the spawn point actually
        # sits in the level. Move the spawn marker in the editor to the road
        # band, and this stays correct at any window size for free.
        spawn = self.level.get_spawn_point(
            default=(self.viewport_size[0] / 2, self.viewport_size[1] / 2))
        self.camera.follow(spawn)

        self.time_in_scene = 0.0
        self._build_impact_fx()

    def handle_event(self, event):
        if self.time_in_scene < self.MIN_DISPLAY_TIME:
            return
        if event.type == pygame.KEYDOWN:
            if event.key in self.ADVANCE_KEYS:
                self._advance()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self._advance()

    def _advance(self):
        if self.next_state is not None:
            self.manager.switch(self.next_state, size=self.size)
        else:
            self.manager.pop()

    def _camera_rect(self):
        return pygame.Rect(round(self.camera.offset.x), round(self.camera.offset.y),
                           round(self.viewport_size[0]), round(self.viewport_size[1]))

    def update(self, dt):
        self.time_in_scene += dt
        self.camera.update(dt)

    def draw(self, surface):
        camera_rect = self._camera_rect()
        shot = pygame.Surface(camera_rect.size)
        shot.fill((25, 35, 60))
        # Layer 1 (car/bike/victim) has to draw after the impact fx, or
        # the ground tiles it shares a pass with would just paint over
        # the shadow/skid marks. Layer 0 is the road surface itself.
        self.level.draw(shot, camera_rect, exclude_layers=(1,))
        self._blit_impact_fx(shot, camera_rect)
        self.level.draw(shot, camera_rect, exclude_layers=(0,))
        pygame.transform.scale(shot, surface.get_size(), surface)
        if self.time_in_scene >= self.MIN_DISPLAY_TIME:
            self._draw_prompt(surface)


    def _draw_prompt(self, surface):

        alpha = int(140 + 100 * math.sin(self.time_in_scene * 3))
        text_surf = PixelFont().render("Press Space", False, (255, 255, 255))
        text_surf.set_alpha(alpha)
        rect = text_surf.get_rect(midbottom=(surface.get_width() // 2, surface.get_height() - 16))
        surface.blit(text_surf, rect)
