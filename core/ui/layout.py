# core/states screens (menu/options/pause) size their widgets with pixel
# constants tuned by eye against this resolution. ui_scale() turns those
# constants into a factor that keeps the same layout proportions on any
# smaller virtual canvas (e.g. main.py's "quarter the window" pixel-art
# setup) instead of overflowing it.
REFERENCE_SIZE = (960, 540)


def ui_scale(size, reference=REFERENCE_SIZE):
    """Factor to shrink REFERENCE_SIZE-tuned pixel constants by so a layout
    still fits within `size`. Capped at 1.0 - a virtual canvas larger than
    the reference doesn't blow widgets up, only smaller canvases shrink
    them."""
    width, height = size
    return min(1.0, width / reference[0], height / reference[1])


def scaled(value, scale, minimum=1):
    """Scale a reference-resolution pixel constant, rounded and floored at
    `minimum` so widgets (and the text inside them) never shrink to 0."""
    return max(minimum, round(value * scale))
