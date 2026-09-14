import colorsys
import xml.etree.ElementTree as ET

from openrvdas_diagram.logger_inventory_builder import Logger, LoggerInventory, Reader, Transform, Writer

'''
Assumptions:
    - Logger names == source name
    - Sources with the same name are the same source
    - Destinations with the same identifying kwarg value are the same destination
'''

GRAPHML_NAMESPACE = "http://graphml.graphdrawing.org/xmlns"
XSI_NAMESPACE = "http://www.w3.org/2001/XMLSchema-instance"
YFILES_NAMESPACE = "http://www.yworks.com/xml/graphml"

ET.register_namespace("y", YFILES_NAMESPACE)

GROUP_COLOR_LIGHTNESS = 0.90
GROUP_COLOR_SATURATION = 0.45
GOLDEN_RATIO_CONJUGATE = 0.618033988749895

NODE_HEIGHT_PX = 50
NODE_MIN_WIDTH_PX = 80
NODE_LABEL_CHAR_WIDTH_PX = 8


def estimate_node_width(label):
    """
    Calculate correct node width based on the label.

    yEd doesn't grow a node to fit its label on its own.  The Geometry we emit
    is the only thing that gives the label room, so it has to be sized up front.
    """
    return max(NODE_MIN_WIDTH_PX, len(label) * NODE_LABEL_CHAR_WIDTH_PX)


def generate_group_color(group_index):
    """
    Returns a light/pastel hex color for the given group index.

    Hues step around the color wheel by the golden ratio conjugate, which spreads
    any number of hues evenly with no two ever landing close together.
    #TODO: Use only colorblind safe colors
    """
    hue = (group_index * GOLDEN_RATIO_CONJUGATE) % 1.0
    red, green, blue = colorsys.hls_to_rgb(hue, GROUP_COLOR_LIGHTNESS, GROUP_COLOR_SATURATION)
    return f"#{round(red * 255):02X}{round(green * 255):02X}{round(blue * 255):02X}"

openrvdas_remote_writer_classes = {
    "CachedDataWriter": "data_server",
    "DatabaseWriter": "host",
    "EmailWriter": "to",
    "FileWriter": "filename",
    "GoogleSheetsWriter": "worksheet_name",
    "GrafanaLiveWriter": "host",
    "InfluxDBWriter": "url",
    "LogfileWriter": "filebase",
    "LoggerManagerWriter": "database | api",
    "MQTTWriter": "broker",
    "NetworkWriter": "network",
    "RedisWriter": "channel",
    "RegexLogfileWriter": "filebase",
    "SealogWriter": "url",
    "SerialWriter": "port",
    "SocketWriter": "channel",
    "TCPWriter": "destination",
    "TextFileWriter": "filename",
    "UDPWriter": "destination",
    "WebsocketWriter": "uri",
}

openrvdas_local_writer_classes = {
    "FileWriter",
    "TextFileWriter",
    "LogfileWriter",
    "RegexLogfileWriter",
    "RecordScreenWriter",
}

class GraphmlBuilder:
    """Builds a yEd-compatible GraphML data-flow diagram from the logger
    inventory returned by LoggerInventoryBuilder."""

    def __init__(self, inventory):
        self.inventory = inventory

        self.nodes = {
            "sources": set(),
            "loggers": {},
            "destinations": {},
        }
        self.edges = []

        self._build_nodes()
        self._build_edges()

    def _build_nodes(self):
        self.nodes["loggers"] = dict(self.inventory)
        self.nodes["sources"] = {
            logger_name
            for logger_definitions in self.inventory.values()
            for logger_name in logger_definitions
        }

        for yaml_file, logger_definitions in self.inventory.items():
            for logger_name, logger in logger_definitions.items():
                for writer in logger.writers:
                    self._add_destination(yaml_file, logger_name, writer)

    def _build_edges(self):
        for yaml_file, logger_definitions in self.nodes["loggers"].items():
            for logger_name in logger_definitions:
                self.edges.append((logger_name, (yaml_file, logger_name), "source_to_logger"))

        for destination_value, logger_refs in self.nodes["destinations"].items():
            for yaml_file, logger_name in logger_refs:
                self.edges.append(((yaml_file, logger_name), destination_value, "logger_to_destination"))

    def _add_destination(self, yaml_file, logger_name, writer):
        if writer.class_name in openrvdas_local_writer_classes:
            return
        destination_kwarg = openrvdas_remote_writer_classes.get(writer.class_name)
        if destination_kwarg is None:
            self.nodes["destinations"].setdefault(writer.class_name, []).append((yaml_file, logger_name))
            return
        for kwarg_name in destination_kwarg.split(" | "):
            if kwarg_name in writer.kwargs:
                destination_value = writer.kwargs[kwarg_name]
                self.nodes["destinations"].setdefault(destination_value, []).append(
                    (yaml_file, logger_name)
                )
                return

    @staticmethod
    def _loggers_are_linked(yaml_file_2, logger_1, logger_2):
        """True if a writer in logger_1 sends to logger_2's yaml file, on a port
        logger_2 also reads from."""
        for writer in logger_1.writers:
            if writer.kwargs.get("destination") != yaml_file_2:
                continue
            writer_port = writer.kwargs.get("port")
            if writer_port is None:
                continue
            if any(reader.kwargs.get("port") == writer_port for reader in logger_2.readers):
                return True
        return False

    @staticmethod
    def _source_node_id(source_name):
        return f"source::{source_name}"

    @staticmethod
    def _logger_node_id(yaml_file, logger_name):
        return f"logger::{yaml_file}::{logger_name}"

    @staticmethod
    def _destination_node_id(destination_value):
        return f"destination::{destination_value}"

    def _edge_endpoint_ids(self, from_id, to_id, kind):
        if kind == "source_to_logger":
            yaml_file, logger_name = to_id
            return self._source_node_id(from_id), self._logger_node_id(yaml_file, logger_name)
        if kind == "logger_to_destination":
            yaml_file, logger_name = from_id
            return self._logger_node_id(yaml_file, logger_name), self._destination_node_id(to_id)
        raise ValueError(f"unknown edge kind: {kind!r}")

    @staticmethod
    def _generate_node_xml(graph, node_id, label, shape):
        node = ET.SubElement(graph, "node", {"id": node_id})
        data = ET.SubElement(node, "data", {"key": "node_graphics"})
        shape_node = ET.SubElement(data, f"{{{YFILES_NAMESPACE}}}ShapeNode")
        ET.SubElement(shape_node, f"{{{YFILES_NAMESPACE}}}Geometry", {"width": str(estimate_node_width(label)), "height": str(NODE_HEIGHT_PX)})
        ET.SubElement(shape_node, f"{{{YFILES_NAMESPACE}}}Shape", {"type": shape})
        ET.SubElement(shape_node, f"{{{YFILES_NAMESPACE}}}BorderStyle", {"type": "line", "width": "1.0", "color": "#000000"})
        ET.SubElement(shape_node, f"{{{YFILES_NAMESPACE}}}NodeLabel", {"autoSizePolicy": "content"}).text = label

    @staticmethod
    def _generate_group_node_xml(graph, group_id, label, fill_color):
        group_node = ET.SubElement(graph, "node", {"id": group_id, "yfiles.foldertype": "group"})
        data = ET.SubElement(group_node, "data", {"key": "node_graphics"})
        proxy = ET.SubElement(data, f"{{{YFILES_NAMESPACE}}}ProxyAutoBoundsNode")
        realizers = ET.SubElement(proxy, f"{{{YFILES_NAMESPACE}}}Realizers", {"active": "0"})
        group_node_element = ET.SubElement(realizers, f"{{{YFILES_NAMESPACE}}}GroupNode")
        ET.SubElement(group_node_element, f"{{{YFILES_NAMESPACE}}}Fill", {"color": fill_color, "transparent": "false"})
        ET.SubElement(group_node_element, f"{{{YFILES_NAMESPACE}}}BorderStyle", {"hasColor": "false", "type": "line", "width": "1.0"})
        ET.SubElement(group_node_element, f"{{{YFILES_NAMESPACE}}}NodeLabel").text = label
        ET.SubElement(group_node_element, f"{{{YFILES_NAMESPACE}}}Shape", {"type": "roundrectangle"})
        ET.SubElement(group_node_element, f"{{{YFILES_NAMESPACE}}}State", {"closed": "false", "innerGraphDisplayEnabled": "false"})
        return ET.SubElement(group_node, "graph", {"id": group_id, "edgedefault": "directed"})

    def _add_node_elements(self, graph):
        group_index = 0

        sources_graph = self._generate_group_node_xml(graph, "group_sources", "sources", generate_group_color(group_index))
        group_index += 1
        for source_name in self.nodes["sources"]:
            self._generate_node_xml(
                sources_graph, 
                self._source_node_id(source_name), 
                source_name, 
                "roundrectangle"
            )

        for yaml_file, logger_definitions in self.nodes["loggers"].items():
            loggers_graph = self._generate_group_node_xml(graph, f"group_loggers::{yaml_file}", yaml_file, generate_group_color(group_index))
            group_index += 1
            for logger_name in logger_definitions:
                self._generate_node_xml(loggers_graph, self._logger_node_id(yaml_file, logger_name), logger_name, "roundrectangle")

        destinations_graph = self._generate_group_node_xml(graph, "group_destinations", "destinations", generate_group_color(group_index))
        group_index += 1
        for destination_value in self.nodes["destinations"]:
            self._generate_node_xml(destinations_graph, self._destination_node_id(destination_value), destination_value, "roundrectangle")

    def _add_edge_elements(self, graph):
        for edge_index, (from_id, to_id, kind) in enumerate(self.edges):
            source_id, target_id = self._edge_endpoint_ids(from_id, to_id, kind)
            edge = ET.SubElement(graph, "edge", {"id": f"e{edge_index}", "source": source_id, "target": target_id})
            data = ET.SubElement(edge, "data", {"key": "edge_graphics"})
            polyline_edge = ET.SubElement(data, f"{{{YFILES_NAMESPACE}}}PolyLineEdge")
            ET.SubElement(polyline_edge, f"{{{YFILES_NAMESPACE}}}Arrows", {"source": "none", "target": "standard"})

    def _build_root_element(self):
        root = ET.Element("graphml", {
            "xmlns": GRAPHML_NAMESPACE,
            "xmlns:xsi": XSI_NAMESPACE,
            "xsi:schemaLocation": f"{GRAPHML_NAMESPACE} http://www.yworks.com/xml/schema/graphml/1.1/ygraphml.xsd",
        })
        ET.SubElement(root, "key", {"for": "node", "id": "node_graphics", "yfiles.type": "nodegraphics"})
        ET.SubElement(root, "key", {"for": "edge", "id": "edge_graphics", "yfiles.type": "edgegraphics"})
        graph = ET.SubElement(root, "graph", {"id": "G", "edgedefault": "directed"})

        self._add_node_elements(graph)
        self._add_edge_elements(graph)

        ET.indent(root)
        return root

    def to_xml(self):
        root = self._build_root_element()
        return ET.tostring(root, encoding="unicode", xml_declaration=True)
