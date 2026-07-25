class GameState:


    def __init__(self, manager):
        self.manager = manager

    def enter(self, **kwargs):
        pass

    def exit(self):
        pass

    def handle_event(self, event):
        pass

    def update(self, dt):
        pass

    def draw(self, surface):
        pass


class StateManager:


    def __init__(self):
        self._stack = []

    @property
    def current(self):
        return self._stack[-1] if self._stack else None

    def push(self, state, **kwargs):
        if self.current:
            self.current.exit()
        self._stack.append(state)
        state.enter(**kwargs)

    def pop(self, **kwargs):
        if not self._stack:
            return
        self._stack.pop().exit()
        if self.current:
            self.current.enter(**kwargs)

    def switch(self, state, **kwargs):
        if self._stack:
            self._stack.pop().exit()
        self._stack.append(state)
        state.enter(**kwargs)

    def reset(self, state, **kwargs):

        while self._stack:
            self._stack.pop().exit()
        self._stack.append(state)
        state.enter(**kwargs)

    def handle_event(self, event):
        if self.current:
            self.current.handle_event(event)

    def update(self, dt):
        if self.current:
            self.current.update(dt)

    def draw(self, surface):

        for state in self._stack:
            state.draw(surface)
