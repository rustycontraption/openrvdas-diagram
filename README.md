# openrvdas-diagram

Generates a data-flow diagram from OpenRVDAS logger configuration files.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

```bash
openrvdas-diagram
```

The output is yEd-compatible GraphML by default. Pass `--graphml-format generic` to write
standard GraphML that other graph tools can read.

### Errors

Problems with the input files, such as a missing include, an unknown `logger_template`, or invalid YAML,
are printed as `error: <message>` and exit with code `3`. Pass `--error-format json` to print them
as JSON for other programs instead:

```json
{"code": "missing_template_file", "message": "...", "details": {"config_file": "ship.yaml", "template_file": "serial_templates.yaml"}}
```

The codes are `missing_template_file`, `unknown_logger_template` and `invalid_yaml`. Any other failure
is a bug and exits with code `1` and a traceback.

### Rendering a PNG

Rendering needs [Graphviz](https://graphviz.org/) installed on the system:

```bash
sudo apt install graphviz
```

Generate generic GraphML, then render it with a layered layout:

```bash
openrvdas-diagram --graphml-format generic
openrvdas-diagram-render data-flow-generated.graphml
```

This writes `data-flow-generated.png`. Use `--output` to choose a different file.

### Color schemes

`openrvdas-diagram-render` takes `--color-scheme`, which sets every color in the rendered PNG:

| Scheme | Colors |
|---|---|
| `classic` (default) | Strong colors from around the color wheel |
| `viridis` | The full [viridis](https://cran.r-project.org/web/packages/viridis/vignettes/intro-to-viridis.html) colormap, from dark purple to yellow |

Viridis stays distinguishable for people with color vision deficiencies.

```bash
openrvdas-diagram --graphml-format generic
openrvdas-diagram-render data-flow-generated.graphml --color-scheme viridis
```

Colors are chosen when rendering, so the same generic GraphML can be drawn in any scheme. The yEd output from
`openrvdas-diagram` always uses the `classic` colors; they can be changed in yEd itself.

#### How schemes work

Every scheme works the same way. A scheme has one pool of colors plus a few fixed colors (node fill, default node
border, default edge color, text and background). Each item's color is picked from the pool by stepping the golden
ratio along it, so items next to each other get clearly different colors, and adding items never changes the colors of
existing ones. Nodes that get their own color (sources and destinations) and the edges connected to them use the
picked color as it is. Group boxes use it mixed 80% of the way toward the background (white unless the scheme sets
one), so labels stay readable on them. Schemes differ only in their pool and fixed colors.

A pool is either:
* `HueWheelPool(lightness, saturation)`: every hue at one lightness and saturation (used by `classic`).
* `StopsPool(stops)`: the colors blended along a list of hex stops (used by `viridis`).

From Python, pass a scheme to `GraphmlRenderer`, either a built-in one or your own `ColorScheme`:

```python
from openrvdas_diagram.color_schemes import ColorScheme, StopsPool, get_color_scheme
from openrvdas_diagram.graphml_renderer import GraphmlRenderer

png_bytes = GraphmlRenderer(graphml_text, color_scheme=get_color_scheme("viridis")).to_png()

my_scheme = ColorScheme(
    name="my-scheme",
    color_pool=StopsPool(("#1A73E8", "#D93025", "#188038")),
    node_fill_color="#FFFFFF",
    default_node_border_color="#222222",
    default_edge_color="#777777",
    text_color="#111111",
    background_color="#FAFAFA",
)
png_bytes = GraphmlRenderer(graphml_text, color_scheme=my_scheme).to_png()
```
