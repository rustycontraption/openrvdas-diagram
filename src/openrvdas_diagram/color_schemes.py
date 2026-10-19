"""
Color schemes for the rendered diagram.

A scheme is a list of colors plus a few fixed colors. Each scheme comes in a
light and a dark version, with colors chosen to show up on that background.

Nodes step through the list (see pick_color), so nodes next to each other get
clearly different colors. Groups mix their picked color towards the background
color.
"""

import math
from dataclasses import dataclass

GOLDEN_RATIO_CONJUGATE = 0.618033988749895
# How far a group box fill is mixed from its picked color toward the background
GROUP_FILL_BACKGROUND_MIX = 0.8
# The background of PNG output when a scheme sets none
DEFAULT_BACKGROUND_COLOR = "#FFFFFF"

# Seven evenly spaced hues around the color wheel, dark enough to show up on white
CLASSIC_LIGHT_COLORS = (
    "#BD0F0F", "#BDA40F", "#41BD0F", "#0FBD72", "#0F72BD", "#410FBD", "#BD0FA4",
)
# The same seven hues, light enough to show up on a dark background
CLASSIC_DARK_COLORS = (
    "#ED5E5E", "#EDD95E", "#87ED5E", "#5EEDB0", "#5EB0ED", "#875EED", "#ED5ED9",
)
# Seven samples of matplotlib's viridis colormap from dark purple to green,
# leaving out the pale yellow end that is hard to see on white
VIRIDIS_LIGHT_COLORS = (
    "#440154", "#45337D", "#365D8C", "#27818D", "#22A485", "#53C468", "#ffcf20FF",
)
# VIRIDIS_LIGHT_COLORS = (
#     "#440154","#3a5e8cFF", "#2f9aa0FF", "#53C468", "#ffcf20FF",
# )
# Seven samples of viridis from blue to yellow, leaving out the near-black
# purple end that is hard to see on a dark background
VIRIDIS_DARK_COLORS = (
    "#414487", "#306A8D", "#228F8C", "#2EB07D", "#70CE57", "#CEE126", "#FDE725",
)

DARK_BACKGROUND_COLOR = "#1E1E1E"


def hex_to_rgb(hex_color):
    """Returns the red, green and blue channels of a #RRGGBB color as 0-255 integers."""
    hex_digits = hex_color.lstrip("#")
    return tuple(int(hex_digits[channel_start:channel_start + 2], 16) for channel_start in (0, 2, 4))


def rgb_to_hex(red, green, blue):
    return f"#{round(red):02X}{round(green):02X}{round(blue):02X}"


def mix_colors(color, other_color, amount):
    """Moves `color` toward `other_color`; amount 0.0 keeps `color`, 1.0 gives `other_color`."""
    return rgb_to_hex(*(
        channel + (other_channel - channel) * amount
        for channel, other_channel in zip(hex_to_rgb(color), hex_to_rgb(other_color))
    ))


def color_step(color_count):
    """
    How many places to move through a list of `color_count` colors for each node.

    About 0.618 of the list (the golden ratio), so consecutive nodes land far
    apart, and sharing no factor with `color_count`, so every color is used once
    before any repeats.
    """
    target_step = round(color_count * GOLDEN_RATIO_CONJUGATE)
    steps_nearest_first = sorted(range(1, color_count + 1), key=lambda step: abs(step - target_step))
    return next(step for step in steps_nearest_first if math.gcd(step, color_count) == 1)


def pick_color(colors, index):
    """Returns the color for item `index`, stepping through `colors` so neighboring items differ."""
    return colors[(index * color_step(len(colors))) % len(colors)]


@dataclass(frozen=True)
class ColorScheme:
    """
    The colors of a diagram.

    colors                      the list node, edge and group box colors are picked from
    node_fill_color             fills node boxes
    default_node_border_color   outlines nodes that have no color of their own
    default_edge_color          colors edges that have no color of their own
    text_color                  colors labels; None keeps the Graphviz default
    background_color            fills the background of PNG output (white if None); DOT/SVG output has no background
    """

    name: str
    colors: tuple
    node_fill_color: str
    default_node_border_color: str
    default_edge_color: str
    text_color: str | None = None
    background_color: str | None = None

    def node_color(self, node_index):
        """
        Picks a node's color from the list.
        """
        return pick_color(self.colors, node_index)

    def group_fill_color(self, group_index):
        background_color = self.background_color or DEFAULT_BACKGROUND_COLOR
        return mix_colors(pick_color(self.colors, group_index), background_color, GROUP_FILL_BACKGROUND_MIX)


CLASSIC_LIGHT = ColorScheme(
    name="classic-light",
    colors=CLASSIC_LIGHT_COLORS,
    node_fill_color="#FFFFFF",
    default_node_border_color="#000000",
    default_edge_color="#555555",
)

CLASSIC_DARK = ColorScheme(
    name="classic-dark",
    colors=CLASSIC_DARK_COLORS,
    node_fill_color="#2B2B2B",
    default_node_border_color="#BBBBBB",
    default_edge_color="#9A9A9A",
    text_color="#E6E6E6",
    background_color=DARK_BACKGROUND_COLOR,
)

VIRIDIS_LIGHT = ColorScheme(
    name="viridis-light",
    colors=VIRIDIS_LIGHT_COLORS,
    node_fill_color="#FFFFFF",
    default_node_border_color="#333333",
    default_edge_color="#666666",
    text_color="#1A1A1A",
)

VIRIDIS_DARK = ColorScheme(
    name="viridis-dark",
    colors=VIRIDIS_DARK_COLORS,
    node_fill_color="#2B2B2B",
    default_node_border_color="#BBBBBB",
    default_edge_color="#9A9A9A",
    text_color="#E6E6E6",
    background_color=DARK_BACKGROUND_COLOR,
)

COLOR_SCHEMES = {
    color_scheme.name: color_scheme
    for color_scheme in (CLASSIC_LIGHT, CLASSIC_DARK, VIRIDIS_LIGHT, VIRIDIS_DARK)
}
DEFAULT_COLOR_SCHEME_NAME = CLASSIC_LIGHT.name


def get_color_scheme(name):
    try:
        return COLOR_SCHEMES[name]
    except KeyError:
        raise ValueError(f"unknown color scheme: {name!r}, expected one of {tuple(COLOR_SCHEMES)}") from None
