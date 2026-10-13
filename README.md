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
