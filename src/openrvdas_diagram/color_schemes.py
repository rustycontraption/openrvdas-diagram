"""
Color schemes for the rendered diagram.

A scheme has one pool of colors plus a few fixed colors.  

Colors are picked from the pool by golden-ratio stepping, so items next to each 
other get clearly different colors. Groups mix their picked color towards the background
color.
"""

import colorsys
from dataclasses import dataclass

GOLDEN_RATIO_CONJUGATE = 0.618033988749895
# How far a group box fill is mixed from its picked color toward the background
GROUP_FILL_BACKGROUND_MIX = 0.8
# Graphviz draws on white when a scheme sets no background
DEFAULT_BACKGROUND_COLOR = "#FFFFFF"

# Evenly spaced samples of matplotlib's viridis colormap, from 0.0 to 1.0
VIRIDIS_STOPS = (
    "#440154", "#482475", "#414487", "#355F8D", "#2A788E", "#21918C",
    "#22A884", "#44BF70", "#7AD151", "#BDDF26", "#FDE725",
)


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


@dataclass(frozen=True)
class HueWheelPool:
    """Every hue at one lightness and saturation; position 0.0 and 1.0 are both red."""

    lightness: float
    saturation: float

    def color_at_position(self, position):
        red, green, blue = colorsys.hls_to_rgb(position, self.lightness, self.saturation)
        return rgb_to_hex(red * 255, green * 255, blue * 255)


@dataclass(frozen=True)
class StopsPool:
    """The colors along a list of hex stops, blended evenly from the first stop (0.0) to the last (1.0)."""

    stops: tuple

    def color_at_position(self, position):
        scaled_position = min(max(position, 0.0), 1.0) * (len(self.stops) - 1)
        lower_stop_index = min(int(scaled_position), len(self.stops) - 2)
        return mix_colors(
            self.stops[lower_stop_index],
            self.stops[lower_stop_index + 1],
            scaled_position - lower_stop_index,
        )


def pick_color(color_pool, index):
    """
    Returns the color for item `index` from a pool.

    Each item steps the golden ratio conjugate further along the pool, so
    consecutive items land far apart and every item keeps its color however many
    items there are.
    """
    return color_pool.color_at_position((index * GOLDEN_RATIO_CONJUGATE) % 1.0)


@dataclass(frozen=True)
class ColorScheme:
    """
    The colors of a diagram.

    color_pool                  the pool node, edge and group box colors are picked from
    node_fill_color             fills node boxes
    default_node_border_color   outlines nodes that have no color of their own
    default_edge_color          colors edges that have no color of their own
    text_color                  colors labels; None keeps the Graphviz default
    background_color            fills the background; None keeps the Graphviz default
    """

    name: str
    color_pool: object
    node_fill_color: str
    default_node_border_color: str
    default_edge_color: str
    text_color: str | None = None
    background_color: str | None = None

    def node_color(self, node_index):
        """
        Picks a node's color from the pool.
        """
        return pick_color(self.color_pool, node_index)

    def group_fill_color(self, group_index):
        background_color = self.background_color or DEFAULT_BACKGROUND_COLOR
        return mix_colors(pick_color(self.color_pool, group_index), background_color, GROUP_FILL_BACKGROUND_MIX)


CLASSIC = ColorScheme(
    name="classic",
    color_pool=HueWheelPool(lightness=0.40, saturation=0.85),
    node_fill_color="#FFFFFF",
    default_node_border_color="#000000",
    default_edge_color="#555555",
)

VIRIDIS = ColorScheme(
    name="viridis",
    color_pool=StopsPool(VIRIDIS_STOPS),
    node_fill_color="#FFFFFF",
    default_node_border_color="#333333",
    default_edge_color="#666666",
    text_color="#1A1A1A",
)

COLOR_SCHEMES = {color_scheme.name: color_scheme for color_scheme in (CLASSIC, VIRIDIS)}
DEFAULT_COLOR_SCHEME_NAME = CLASSIC.name


def get_color_scheme(name):
    try:
        return COLOR_SCHEMES[name]
    except KeyError:
        raise ValueError(f"unknown color scheme: {name!r}, expected one of {tuple(COLOR_SCHEMES)}") from None
