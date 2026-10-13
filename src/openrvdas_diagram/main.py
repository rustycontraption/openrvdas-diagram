import argparse
from pathlib import Path

from openrvdas_diagram.graphml_builder import (
    GRAPHML_FORMAT_YED,
    SUPPORTED_GRAPHML_FORMATS,
    GraphmlBuilder,
)
from openrvdas_diagram.logger_inventory_builder import LoggerInventoryBuilder


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config-dir", default="openrvdas", help="Directory containing the OpenRVDAS logger config files"
    )
    parser.add_argument(
        "--template-dir", default="openrvdas/logger_templates", help="Directory containing the logger templates"
    )
    parser.add_argument(
        "--graphml-format",
        choices=SUPPORTED_GRAPHML_FORMATS,
        default=GRAPHML_FORMAT_YED,
        help="Which GraphML flavor to write: yed for yEd styling and groups, generic for standard GraphML only. Default is yEd format",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    inventory = LoggerInventoryBuilder().collectAndParseLoggers(
        config_dir=args.config_dir, template_dir=args.template_dir
    )
    xml = GraphmlBuilder(inventory, graphml_format=args.graphml_format).to_xml()
    out_path = Path("data-flow-generated.graphml")
    out_path.write_text(xml)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
