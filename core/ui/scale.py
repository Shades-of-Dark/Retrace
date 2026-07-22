# The width core/states' UI layout constants (panel widths, button sizes,
# gaps, font scales) were originally tuned against - ui_scale(width) turns
# an actual canvas width into a multiplier those constants get scaled by,
# so shrinking/growing the virtual resolution (main.py's VIRTUAL_WIDTH)
# shrinks/grows the UI proportionally with it instead of the UI staying a
# fixed absolute size while the canvas around it changes.
UI_REFERENCE_WIDTH = 960


def ui_scale(width):
    return width / UI_REFERENCE_WIDTH
