# Neutral default look for every widget. Override per-game by passing a
# theme dict (same keys) into any widget, or into Panel to cascade it -
# real art should live in assets/palette_ui/ once a game supplies it.
DEFAULT_THEME = {
    "bg": (40, 42, 54),
    "bg_hover": (55, 58, 70),
    "bg_pressed": (30, 32, 40),
    "border": (90, 94, 110),
    "text": (230, 230, 235),
    "text_disabled": (120, 120, 125),
    "accent": (100, 170, 235),
    "track": (60, 62, 74),
}
