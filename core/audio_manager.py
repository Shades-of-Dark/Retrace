import pygame


class AudioManager:
    """Sound/music playback. Doesn't know any specific game's sound names -
    the game layer calls load_sounds() with its own name -> filepath map.
    Fails soft (no crash) if there's no audio device available."""

    def __init__(self):
        self.available = True
        if pygame.mixer.get_init() is None:
            try:
                pygame.mixer.init()
            except pygame.error:
                self.available = False

        self.sounds = {}
        self.sfx_volume = 1.0
        self.music_volume = 1.0
        self.muted = False
        self._current_music_path = None

    def load_sounds(self, sound_map):
        """sound_map: {"jump": "assets/sfx/jump.wav", ...}"""
        if not self.available:
            return
        for name, path in sound_map.items():
            self.sounds[name] = pygame.mixer.Sound(path)

    def play(self, name, volume=1.0):
        if not self.available or self.muted or name not in self.sounds:
            return
        sound = self.sounds[name]
        sound.set_volume(volume * self.sfx_volume)
        sound.play()

    def play_music(self, path, loops=-1, fade_ms=0, volume=None):
        if not self.available:
            return
        if self._current_music_path == path:
            # Same track already loaded (playing or paused) - just make
            # sure it's audible rather than reloading and restarting it
            # from 0. Lets quick memory<->timeline<->memory hops resume
            # in place instead of feeling like a hard restart each time.
            pygame.mixer.music.unpause()
            return
        pygame.mixer.music.load(path)
        target_volume = volume if volume is not None else self.music_volume
        pygame.mixer.music.set_volume(0 if self.muted else target_volume)
        pygame.mixer.music.play(loops, fade_ms=fade_ms)
        self._current_music_path = path

    def pause_music(self):
        if not self.available:
            return
        pygame.mixer.music.pause()

    def stop_music(self, fade_ms=0):
        if not self.available:
            return
        if fade_ms:
            pygame.mixer.music.fadeout(fade_ms)
        else:
            pygame.mixer.music.stop()
        self._current_music_path = None

    def set_sfx_volume(self, volume):
        self.sfx_volume = max(0.0, min(1.0, volume))

    def set_music_volume(self, volume):
        self.music_volume = max(0.0, min(1.0, volume))
        if self.available:
            pygame.mixer.music.set_volume(0 if self.muted else self.music_volume)

    def set_muted(self, muted):
        self.muted = muted
        if self.available:
            pygame.mixer.music.set_volume(0 if muted else self.music_volume)
