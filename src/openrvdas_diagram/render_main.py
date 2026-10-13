import argparse
import sys
from pathlib import Path

import graphviz

from openrvdas_diagram.graphml_renderer import GraphmlRenderer


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "graphml_file", help="Generic-format GraphML file written by openrvdas-diagram --graphml-format generic"
    )
    parser.add_argument(
        "--output", help="Where to write the PNG. Default is the GraphML file name with a .png extension"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    graphml_path = Path(args.graphml_file)
    out_path = Path(args.output) if args.output else graphml_path.with_suffix(".png")

    try:
        png_bytes = GraphmlRenderer(graphml_path.read_text()).to_png()
    except ValueError as error:
        sys.exit(f"could not read {graphml_path}: {error}")
    except graphviz.ExecutableNotFound:
        sys.exit("Graphviz is not installed, install it with: sudo apt install graphviz")

    out_path.write_bytes(png_bytes)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
