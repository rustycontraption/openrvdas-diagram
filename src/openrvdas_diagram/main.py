import argparse
import json
import sys
from pathlib import Path

from openrvdas_diagram.graphml_builder import (
    GRAPHML_FORMAT_YED,
    SUPPORTED_GRAPHML_FORMATS,
    GraphmlBuilder,
)
from openrvdas_diagram.errors import UserInputError
from openrvdas_diagram.logger_inventory_builder import LoggerInventoryBuilder

ERROR_FORMAT_TEXT = "text"
ERROR_FORMAT_JSON = "json"
# Distinct from argparse usage errors (2) and uncaught exceptions (1)
USER_INPUT_ERROR_EXIT_CODE = 3


def parse_args(argv=None):
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
    parser.add_argument(
        "--error-format",
        choices=(ERROR_FORMAT_TEXT, ERROR_FORMAT_JSON),
        default=ERROR_FORMAT_TEXT,
        help="How to print problems with the input files: text for people, json for programs. Default is text",
    )
    return parser.parse_args(argv)


def report_user_input_error(error, error_format):
    if error_format == ERROR_FORMAT_JSON:
        print(json.dumps(error.to_dict()), file=sys.stderr)
    else:
        print(f"error: {error.message}", file=sys.stderr)


def main(argv=None):
    args = parse_args(argv)
    try:
        inventory = LoggerInventoryBuilder().collectAndParseLoggers(
            config_dir=args.config_dir, template_dir=args.template_dir
        )
    except UserInputError as error:
        report_user_input_error(error, args.error_format)
        sys.exit(USER_INPUT_ERROR_EXIT_CODE)
    xml = GraphmlBuilder(inventory, graphml_format=args.graphml_format).to_xml()
    out_path = Path("data-flow-generated.graphml")
    out_path.write_text(xml)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
