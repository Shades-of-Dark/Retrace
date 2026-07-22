import pygame


class InputManager:
    """Tracks raw key/mouse state (down / just-pressed / just-released) and
    maps it to named actions via bindings the game layer supplies, e.g.:

        InputManager({"jump": [pygame.K_SPACE, pygame.K_w]})

    Core has no idea what "jump" means - it just resolves the key list.
    """

    def __init__(self, bindings=None):
        self.bindings = bindings or {}
        self._down = set()
        self._pressed = set()
        self._released = set()
        self.mouse_pos = pygame.Vector2()
        self.mouse_down = set()
        self.mouse_pressed = set()
        self.mouse_released = set()

    def set_bindings(self, bindings):
        self.bindings = bindings

    def _begin_frame(self):
        self._pressed.clear()
        self._released.clear()
        self.mouse_pressed.clear()
        self.mouse_released.clear()

    def _process_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key not in self._down:
                self._pressed.add(event.key)
            self._down.add(event.key)
        elif event.type == pygame.KEYUP:
            self._down.discard(event.key)
            self._released.add(event.key)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self.mouse_down.add(event.button)
            self.mouse_pressed.add(event.button)
        elif event.type == pygame.MOUSEBUTTONUP:
            self.mouse_down.discard(event.button)
            self.mouse_released.add(event.button)
        elif event.type == pygame.MOUSEMOTION:
            self.mouse_pos.update(event.pos)

    def update(self, events):
        """Call once per frame with the full list of pygame events."""
        self._begin_frame()
        for event in events:
            self._process_event(event)

    def key_down(self, key):
        return key in self._down

    def key_pressed(self, key):
        return key in self._pressed

    def key_released(self, key):
        return key in self._released

    def is_action_down(self, action):
        return any(k in self._down for k in self.bindings.get(action, []))

    def is_action_pressed(self, action):
        return any(k in self._pressed for k in self.bindings.get(action, []))

    def is_action_released(self, action):
        return any(k in self._released for k in self.bindings.get(action, []))

    def get_axis(self, negative_action, positive_action):
        value = 0
        if self.is_action_down(negative_action):
            value -= 1
        if self.is_action_down(positive_action):
            value += 1
        return value

    def get_vector(self, left, right, up, down):
        vec = pygame.Vector2(self.get_axis(left, right), self.get_axis(up, down))
        if vec.length_squared() > 0:
            vec = vec.normalize()
        return vec
