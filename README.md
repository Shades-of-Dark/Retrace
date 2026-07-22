# gamejam-template

A reusable Python/Pygame toolkit for game jams. `core/` is a small, generic
engine layer (state management, entities, animation, camera, particles,
input, audio, UI); `game/` is where jam-specific code goes, and starts on
this template with nothing but an empty `PlayState` - the seam where your
actual game begins.

## Structure

```
core/              engine layer - avoid editing during a jam
  state_manager.py
  entity.py
  animation.py
  camera.py         world<->screen offset, follow, bounds, screen shake
  particles.py
  input_manager.py
  audio_manager.py
  pygame_loader.py
  tilemap_loader.py
  pixelfont.py       bitmap font atlas parser/renderer
  display.py        VirtualDisplay - resizable window + resolution scaling
  states/           MenuState, PauseState, OptionsState - see below
  ui/               buttons, sliders, labels, checkboxes, panels
  ui_assets/
    font.png        default pixel font atlas - swap for your own
game/               jam-specific code
  play.py           PlayState - empty on the template, build your game here
assets/
  palette_ui/       reusable neutral UI sprites
  sfx/              sfxr-style sound effects
  music/
main.py             wires core together; owns the menu/play/pause flow
JAM_CHECKLIST.md    process reminders for before / during / after a jam
```

## Quickstart

```
pip install -r requirements.txt
python main.py
```

Running `main.py` on a fresh clone opens straight to a menu (Start /
Options / Quit) built from nothing but `core/`. Start drops you into
`game/play.py`'s `PlayState` - currently just a fill color, Escape to pause
- that's the seam where your game plugs in. That's the cold-start test - if
the menu doesn't open or the flow breaks, the template is broken, not your
game.

## Screen flow

`main.py` wires the three `core/states/` screens together with
`StateManager` (`core/state_manager.py`), plus `game/play.py`'s `PlayState`:

- **`MenuState`** (`core/states/menu.py`) - Start / Options / Quit. Generic:
  you pass it an `on_start` callback and it doesn't know or care what
  "start" means.
- **`PlayState`** (`game/play.py`) - your game. On the template it's
  intentionally empty (fill color, Escape to pause) - build your actual
  gameplay here, or replace it entirely with your own state(s).
- **`PauseState`** (`core/states/pause.py`) - Resume / Options / Quit to
  menu. Pushed on top of whatever's playing (Escape from `PlayState` does
  this), so `StateManager` freezes the state underneath and renders it
  dimmed behind the pause panel.
- **`OptionsState`** (`core/states/options.py`) - music/SFX sliders + mute,
  wired to `AudioManager`. Pushable from either the menu or the pause
  screen; Back/Escape pops it back to whichever pushed it.

### Plugging in your actual game

Build directly in `game/play.py`'s `PlayState`, or add new files/classes to
`game/` and point `build_play_state()` in `main.py` at whichever one should
run first:

```python
def build_play_state(states, input_manager, audio_manager):
    return PlayState(
        states, input_manager, audio_manager,
        size=(VIRTUAL_WIDTH, VIRTUAL_HEIGHT),
        on_quit_to_menu=lambda: states.reset(build_menu_state(states, input_manager, audio_manager)),
    )
```

Whatever you push here should subclass `core.state_manager.GameState`.
Everything else - the menu, pause, options, and quit-to-menu wiring - keeps
working unchanged, since none of it references `PlayState` by name outside
this one function.

`PlayState.handle_event` already pushes `PauseState` on Escape, passing
through `on_quit_to_menu` as `PauseState`'s `on_quit`:

```python
if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
    self.manager.push(PauseState(
        self.manager, self.audio, on_quit=self.on_quit_to_menu, size=self.size))
```

`on_quit` is optional on `PauseState` - omit it and the "Quit to menu"
button disappears, leaving just Resume/Options.

## Resolution scaling

The window (created in `main()`) is resizable, and everything - your game
and every `core/ui` widget - draws onto a fixed-size virtual surface that
`core/display.py`'s `VirtualDisplay` scales up (or down) to fill it,
letterboxed to preserve aspect ratio. This is the standard "draw small,
scale up" approach: author your UI once against a fixed resolution and it
stays correctly laid out at any window size, because the whole rendered
frame - UI included - is scaled as one image rather than each widget
repositioning itself.

Two constants in `main.py` control it:

```python
WINDOW_WIDTH = 960    # real OS window, starting size (user can resize)
WINDOW_HEIGHT = 540
VIRTUAL_WIDTH = WINDOW_WIDTH    # what you actually draw at
VIRTUAL_HEIGHT = WINDOW_HEIGHT
```

They match 1:1 by default, so resizing the window just scales the existing
960x540 layout up or down - nothing looks different at the starting size.
For a lower-res pixel-art look (the "half or quarter the window" pattern),
drop `VIRTUAL_WIDTH`/`VIRTUAL_HEIGHT`, e.g. to a quarter:

```python
VIRTUAL_WIDTH = WINDOW_WIDTH // 4
VIRTUAL_HEIGHT = WINDOW_HEIGHT // 4
```

`VirtualDisplay` defaults to nearest-neighbor scaling (`smooth=False`),
which is what keeps pixel art crisp instead of blurry at non-integer
scale factors; pass `smooth=True` if you'd rather have smoothscale.

`core/states`' `MenuState`/`OptionsState`/`PauseState` size their own
buttons/panels/fonts off of `core/ui/layout.py`'s `ui_scale()`, which shrinks
their (960x540-tuned) pixel constants to fit whatever `VIRTUAL_WIDTH`/
`VIRTUAL_HEIGHT` you actually pass as `size` - so dropping to a quarter
resolution shrinks that UI to match instead of overflowing the virtual
canvas. Use the same helper (`ui_scale`/`scaled`, exported from `core.ui`) if
you hand-roll UI in `game/` and want it to scale the same way.

If you build your own `GameState` in `game/`, two rules keep it in sync
with this system:

- Draw onto the `surface` passed to `draw(surface)` - that's already
  `display.surface` (the virtual surface), not the real window. Don't call
  `pygame.display.get_surface()` for layout; if you need the drawable size,
  it's `(VIRTUAL_WIDTH, VIRTUAL_HEIGHT)` from `main.py`.
- Mouse positions in every event your state receives are already in
  virtual-surface coordinates - `main.py`'s loop runs every event through
  `display.handle_event(event)` (which rewrites `event.pos`) before
  `states.handle_event(event)`. You never need to convert them yourself.

## Pixel font

All `core/ui` text (`Button`, `Label`) and every `core/states` title defaults
to `PixelFont` (`core/ui/pixel_font.py`), which renders the bitmap atlas at
`core/ui_assets/font.png` via the parser in `core/pixelfont.py`. It's a
drop-in for `pygame.font.Font` - same `.render(text, antialias, color)` and
`.size(text)` calls - so nothing outside `pixel_font.py` needed to change
to use it.

```python
from core.ui import PixelFont

font = PixelFont(scale=2)                        # integer scale, no smoothing - stays crisp
font = PixelFont(path="assets/my_font.png", scale=3, outline=False)
```

- `scale` - integer multiplier on the atlas's native glyph size (8px tall).
  UI defaults: `2` for buttons/labels, `3`-`4` for state titles.
- `outline`/`outline_color` - the 1px outline drawn around each glyph
  (on by default, black).
- `path` - point it at your own atlas once you have one; it must follow
  the same format as `font.png` (a row-0 marker pixel with `r == 127`
  between glyphs - see `core/pixelfont.py` for the exact parsing rules).

Pass `font=` to any `Button`/`Label` to override the default per-widget, or
swap `DEFAULT_FONT_PATH` in `pixel_font.py` to change the template-wide
default font in one place.

## Screen shake

`Camera.shake(intensity, duration, randomness=1.0)` (`core/camera.py`)
kicks off a shake that decays to 0 over `duration` seconds; call it from
wherever your game logic reacts to an impact:

```python
self.camera.shake(intensity=12, duration=0.3, randomness=0.6)
```

- `intensity` - max offset in pixels at the start of the shake.
- `duration` - seconds until it fades out.
- `randomness` (0-1) - blends between a smooth circular wobble (`0`) and
  fully random per-frame jitter (`1`).

It composes with camera follow/bounds automatically - `apply()`,
`apply_pos()`, and `screen_to_world()` all include the shake offset, and it
works even with no follow target set. A second `shake()` call replaces
whatever shake is already running rather than stacking with it.

## Using this as a template

Enable **Settings -> Template repository** on this repo, then use
"Use this template" on GitHub to start each new jam from a clean copy. See
`JAM_CHECKLIST.md` for the full before/during/after workflow.

## Rules of thumb

- `core/` is generic and config-driven - it should never reference a
  specific game concept (no `if state == "boss_fight"` in `core/`). If
  you're tempted to add one, the code belongs in `game/`.
- Systems take config from the game layer instead of hardcoding it:
  `AudioManager.load_sounds()` takes a name -> file map, `ParticleSystem`
  takes registered presets, `InputManager` takes a bindings dict.
- If you edit `core/` mid-jam, that's a signal you hit a real gap - fix it,
  but do the cleanup in the post-jam retro, not at 2am on day 3.
