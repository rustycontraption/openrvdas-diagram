# openrvdas-diagram

Generates a data-flow diagram from OpenRVDAS logger configuration files.

## Installation

```bash
pip install https://github.com/rustycontraption/openrvdas-diagram/archive/refs/tags/v0.2.1.tar.gz
```

This installs the `openrvdas-diagram` and `openrvdas-diagram-render` commands.

## Usage

```bash
openrvdas-diagram --config-dir path/to/configs --template-dir path/to/logger_templates
```

This writes `data-flow-generated.graphml` in the current directory. Without the options, configs are read from
`openrvdas` and templates from `openrvdas/logger_templates`.

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

Each light and dark version uses colors that show up on its background. Sources, destinations and the edges
connected to them each get their own color, and group boxes get a light tint of theirs.

Viridis stays distinguishable for people with color vision deficiencies.

```bash
openrvdas-diagram --graphml-format generic
openrvdas-diagram-render data-flow-generated.graphml --color-scheme viridis-dark
```

Colors are chosen when rendering, so the same generic GraphML can be drawn in any scheme. The yEd output from
`openrvdas-diagram` always uses the `classic-light` colors; they can be changed in yEd itself.

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

The commands then run from your working copy. Run the tests with:

```bash
pytest
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
