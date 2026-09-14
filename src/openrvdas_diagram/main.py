import argparse
from pathlib import Path

from openrvdas_diagram.graphml_builder import GraphmlBuilder
from openrvdas_diagram.logger_inventory_builder import LoggerInventoryBuilder


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config-dir", default="openrvdas", help="Directory containing the OpenRVDAS logger config files"
    )
    parser.add_argument(
        "--template-dir", default="openrvdas/logger_templates", help="Directory containing the logger templates"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    inventory = LoggerInventoryBuilder().collectAndParseLoggers(
        config_dir=args.config_dir, template_dir=args.template_dir
    )
    xml = GraphmlBuilder(inventory).to_xml()
    out_path = Path("data-flow-generated.graphml")
    out_path.write_text(xml)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
