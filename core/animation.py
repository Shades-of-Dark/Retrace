import pygame


class Animation:
    """A single named sequence of frames. Build these from a spritesheet
    with slice_spritesheet(), or pass in a hand-built frame list."""

    def __init__(self, frames, frame_duration=0.1, loop=True):
        self.frames = frames
        self.frame_duration = frame_duration
        self.loop = loop
        self.timer = 0.0
        self.frame_index = 0
        self.done = False

    def reset(self):
        self.timer = 0.0
        self.frame_index = 0
        self.done = False

    def update(self, dt):
        if self.done:
            return
        self.timer += dt
        while self.timer >= self.frame_duration:
            self.timer -= self.frame_duration
            self.frame_index += 1
            if self.frame_index >= len(self.frames):
                if self.loop:
                    self.frame_index = 0
                else:
                    self.frame_index = len(self.frames) - 1
                    self.done = True
                    break

    @property
    def image(self):
        return self.frames[self.frame_index]


class Animator:
    """Attach to an Entity to manage named Animations and switch between
    them, e.g. animator.play("run")."""

    def __init__(self):
        self.animations = {}
        self.current_name = None

    def add(self, name, animation):
        self.animations[name] = animation

    def play(self, name, restart=False):
        if self.current_name == name and not restart:
            return
        self.current_name = name
        self.animations[name].reset()

    def update(self, dt):
        if self.current_name:
            self.animations[self.current_name].update(dt)

    @property
    def image(self):
        if self.current_name is None:
            return None
        return self.animations[self.current_name].image


def slice_spritesheet(sheet, frame_width, frame_height, count=None):
    """Cuts a horizontal spritesheet Surface into a list of frame Surfaces."""
    sheet_width, _ = sheet.get_size()
    max_frames = sheet_width // frame_width
    if count is None:
        count = max_frames
    frames = []
    for i in range(count):
        rect = pygame.Rect(i * frame_width, 0, frame_width, frame_height)
        frames.append(sheet.subsurface(rect).copy())
    return frames
