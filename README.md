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

| Scheme | Background | Colors |
|---|---|---|
| `classic-light` (default) | White | 7 strong colors from around the color wheel |
| `classic-dark` | Charcoal (`#1E1E1E`) | The same 7 hues, lighter |
| `viridis-light` | White | 7 colors from the [viridis](https://cran.r-project.org/web/packages/viridis/vignettes/intro-to-viridis.html) colormap, dark purple to green |
| `viridis-dark` | Charcoal (`#1E1E1E`) | 7 colors from viridis, blue to yellow |

Each light and dark version uses colors that show up on its background. The background is drawn into PNGs only;
DOT output (`GraphmlRenderer.to_dot()`, e.g. for drawing an SVG on a web page) has a transparent background.

Viridis stays distinguishable for people with color vision deficiencies.

```bash
openrvdas-diagram --graphml-format generic
openrvdas-diagram-render data-flow-generated.graphml --color-scheme viridis-dark
```

Colors are chosen when rendering, so the same generic GraphML can be drawn in any scheme. The yEd output from
`openrvdas-diagram` always uses the `classic-light` colors; they can be changed in yEd itself.

#### How schemes work

Every scheme works the same way. A scheme is a list of colors plus a few fixed colors (node fill, default node border,
default edge color, text and background). Each node that gets its own color (sources and destinations) takes the next
color from the list, stepping about 0.6 of the way through the list each time. That way nodes next to each other get
clearly different colors, and every color is used once before any repeats. The edges connected to a node share its
color. Group boxes use the color mixed 80% of the way toward the background (white unless the scheme sets one), so
labels stay readable on them. Schemes differ only in their list and fixed colors.

From Python, pass a scheme to `GraphmlRenderer`, either a built-in one or your own `ColorScheme`:

```python
from openrvdas_diagram.color_schemes import ColorScheme, get_color_scheme
from openrvdas_diagram.graphml_renderer import GraphmlRenderer

png_bytes = GraphmlRenderer(graphml_text, color_scheme=get_color_scheme("viridis-dark")).to_png()

my_scheme = ColorScheme(
    name="my-scheme",
    colors=("#1A73E8", "#D93025", "#F9AB00", "#188038", "#A142F4", "#E8710A", "#12B5CB"),
    node_fill_color="#FFFFFF",
    default_node_border_color="#222222",
    default_edge_color="#777777",
    text_color="#111111",
    background_color="#FAFAFA",
)
png_bytes = GraphmlRenderer(graphml_text, color_scheme=my_scheme).to_png()
```

## TODO

### Diagram content
* **Loggers that send to each other:** decide how to draw a logger whose writer feeds another logger's reader.
  `GraphmlBuilder._loggers_are_linked` only compares two loggers at a time; it should handle any number of them.
* **Writers that go nowhere:** decide how to show a logger writer whose output reaches no known destination.
* **FileWriters:** decide how to show loggers that write to local files, perhaps as a note on the logger node.
* **Unlisted OpenRVDAS writer classes:** `openrvdas_remote_writer_classes` and `openrvdas_local_writer_classes` in
  `graphml_builder.py` only know the classes listed there. Add default handling for any other OpenRVDAS writer class.

### Layout and colors
* **Colors in the yEd output:** color schemes are imported into `graphml_builder.py` only to color the yEd output.
  Consider leaving yEd output uncolored (yEd can apply its own styling) so all color code stays in the renderer.
* **Measured DOT:** `GraphmlRenderer.to_dot()` gives each edge an attachment point in config order, while `to_png()`
  first measures the layout and orders attachment points by position. Edges drawn from `to_dot()` can bend sharply
  into nodes with many incoming edges. Consider a `to_dot(measure_layout=True)` option (also available from the CLI)
  that returns the measured DOT; it needs Graphviz installed, like `to_png()`.
* **Stable layout:** sources are kept in a set, so their order, and so the layout and colors, can change from run to
  run with the same configs.
