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
