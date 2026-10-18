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

Each light and dark version uses colors that show up on its background.

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
