import pygame

from core.state_manager import GameState
from core.states import PauseState
from core.tilemap_loader import Level
from core.camera import Camera  # adjust path if Camera lives elsewhere
from game.play import PlayState


class Timeline(GameState):
    def __init__(self, manager, timeline_data, input_manager=None, audio_manager=None, on_quit_to_menu=None):
        super().__init__(manager)
        self.level = None
        self.camera = None
        self.size = None
        self.next_state = None
        self.time_in_scene = 0.0
        self.timeline_data = timeline_data
        self.circle_rects = []
        self.input_manager = input_manager
        self.audio_manager = audio_manager
        self.on_quit_to_menu = on_quit_to_menu
        self.mouse_pos = (0, 0)

    def enter(self, size=(960, 540), next_state=None, level_path=None, tilesets_dir=None, **kwargs):
        # self.manager.switch(Timeline(self.manager), size=screen.get_size(), next_state=NextLevelState(self.manager),
        # level_path=..., tilesets_dir=...)
        self.size = size
        self.next_state = next_state

        self.camera = Camera(size[0], size[1], smoothing=0.1)
        self.time_in_scene = 0.0

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.manager.push(PauseState(
                self.manager, self.audio_manager, on_quit=self.on_quit_to_menu, size=self.size))
            return
        if event.type == pygame.MOUSEBUTTONDOWN:
            for i, circle in enumerate(self.circle_rects):
                if self._point_in_circle(circle, event.pos):
                    self._select_event(self.timeline_data["events"][i])
                    break

    @staticmethod
    def _point_in_circle(circle, pos):
        cx, cy = circle["center"]
        dx, dy = pos[0] - cx, pos[1] - cy
        return dx * dx + dy * dy <= circle["radius"] ** 2

    def _select_event(self, event_data):
        level_path = event_data.get("level_path")
        if level_path is None:
            self._advance()
            return

        tilesets_dir = event_data.get("tilesets_dir", "game/assets/images/tilesets")

        def back_to_timeline():
            # Pushed by PlayState -> PauseState, so two pops: close the
            # pause overlay, then leave the memory level itself, landing
            # back on this same Timeline instance underneath. pop() re-runs
            # enter() on whatever it exposes, so the second pop must repass
            # size or Timeline.enter()'s (wrong) 960x540 default sneaks back in.
            self.manager.pop()
            self.manager.pop(size=self.size)

        self.manager.push(
            PlayState(
                self.manager, self.input_manager, self.audio_manager,
                size=self.size,
                on_quit_to_menu=back_to_timeline,
                quit_label="Back to Timeline",
                level_path=level_path,
                tilesets_dir=tilesets_dir,
            )
        )

    def _advance(self):
        if self.next_state is not None:
            self.manager.switch(self.next_state)
        else:
            self.manager.pop()

    def _camera_rect(self):
        return pygame.Rect(round(self.camera.offset.x), round(self.camera.offset.y), self.size[0], self.size[1])

    def update(self, dt):
        self.time_in_scene += dt
        mouse_pos = self.input_manager.mouse_pos if self.input_manager is not None else self.mouse_pos
        for circle in self.circle_rects:
            circle["color"] = (255, 0, 0) if self._point_in_circle(circle, mouse_pos) else (255, 255, 255)

    def draw(self, surface):
        surface.fill((25, 35, 60))
        camera_rect = self._camera_rect()
        width = (surface.get_width() * 3 / 4) - (surface.get_width() / 4)
        x = surface.get_width() // 4
        pygame.draw.line(surface, (255, 255, 255), (
            x, surface.get_height() // 2), (x + width,
                                            surface.get_height() // 2), 2)
        radius = 15
        o = 0
        for thing in self.timeline_data["events"]:
            center = (x + (width * thing["age"] / thing["total_age"]), surface.get_height() // 2 - radius)

            if len(self.circle_rects) < len(self.timeline_data["events"]):
                self.circle_rects.append({"center": center, "radius": radius, "color": (255, 255, 255)})

            pygame.draw.circle(surface, self.circle_rects[o]["color"], center, radius)
            o += 1
