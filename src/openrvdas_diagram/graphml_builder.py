import xml.etree.ElementTree as ET
from dataclasses import dataclass

from openrvdas_diagram.color_schemes import CLASSIC_LIGHT

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

GRAPHML_FORMAT_YED = "yed"
GRAPHML_FORMAT_GENERIC = "generic"
SUPPORTED_GRAPHML_FORMATS = (GRAPHML_FORMAT_YED, GRAPHML_FORMAT_GENERIC)

YED_SCHEMA_LOCATION = "http://www.yworks.com/xml/schema/graphml/1.1/ygraphml.xsd"
GENERIC_SCHEMA_LOCATION = "http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd"

NODE_HEIGHT_PX = 50
NODE_MIN_WIDTH_PX = 80
NODE_LABEL_CHAR_WIDTH_PX = 8


def estimate_node_width(label):
    """
    yEd doesn't grow a node to fit its label on its own.  The Geometry we emit
    is the only thing that gives the label room, so it has to be sized up front.
    """
    return max(NODE_MIN_WIDTH_PX, len(label) * NODE_LABEL_CHAR_WIDTH_PX)


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


@dataclass
class Node:
    node_id: str
    label: str
    kind: str  # "source", "logger" or "destination"
    group_id: str
    group_label: str


@dataclass
class Edge:
    source_node_id: str
    target_node_id: str


class GraphmlBuilder:
    """The yEd output always uses the classic colors; color schemes are chosen when
    rendering generic GraphML with GraphmlRenderer."""

    def __init__(self, inventory, graphml_format=GRAPHML_FORMAT_YED):
        if graphml_format not in SUPPORTED_GRAPHML_FORMATS:
            raise ValueError(
                f"unknown graphml format: {graphml_format!r}, expected one of {SUPPORTED_GRAPHML_FORMATS}"
            )

        self.inventory = inventory
        self.graphml_format = graphml_format

        self.nodes = []
        self.edges = []

        self._build_nodes_and_edges()

    def _build_nodes_and_edges(self):
        self._add_source_nodes()
        logger_node_ids_by_destination_value = self._add_logger_nodes()
        self._add_destination_nodes(logger_node_ids_by_destination_value)

    def _add_source_nodes(self):
        source_names = dict.fromkeys(
            logger_name
            for logger_definitions in self.inventory.values()
            for logger_name in logger_definitions
        )
        for source_name in source_names:
            self.nodes.append(Node(
                node_id=self._source_node_id(source_name),
                label=source_name,
                kind="source",
                group_id="group_sources",
                group_label="sources",
            ))

    def _add_logger_nodes(self):
        logger_node_ids_by_destination_value = {}
        for yaml_file, logger_definitions in self.inventory.items():
            for logger_name, logger in logger_definitions.items():
                logger_node_id = self._logger_node_id(yaml_file, logger_name)
                self.nodes.append(Node(
                    node_id=logger_node_id,
                    label=logger_name,
                    kind="logger",
                    group_id=f"group_loggers::{yaml_file}",
                    group_label=yaml_file,
                ))
                self.edges.append(Edge(
                    source_node_id=self._source_node_id(logger_name),
                    target_node_id=logger_node_id,
                ))
                for writer in logger.writers:
                    destination_value = self._destination_value(writer)
                    if destination_value is not None:
                        logger_node_ids_by_destination_value.setdefault(destination_value, []).append(logger_node_id)
        return logger_node_ids_by_destination_value

    def _add_destination_nodes(self, logger_node_ids_by_destination_value):
        for destination_value, logger_node_ids in logger_node_ids_by_destination_value.items():
            destination_node_id = self._destination_node_id(destination_value)
            self.nodes.append(Node(
                node_id=destination_node_id,
                label=destination_value,
                kind="destination",
                group_id="group_destinations",
                group_label="destinations",
            ))
            for logger_node_id in logger_node_ids:
                self.edges.append(Edge(
                    source_node_id=logger_node_id,
                    target_node_id=destination_node_id,
                ))

    @staticmethod
    def _destination_value(writer):
        if writer.class_name in openrvdas_local_writer_classes:
            return None
        destination_kwarg = openrvdas_remote_writer_classes.get(writer.class_name)
        if destination_kwarg is None:
            return writer.class_name
        for kwarg_name in destination_kwarg.split(" | "):
            if kwarg_name in writer.kwargs:
                return writer.kwargs[kwarg_name]
        return None

    @staticmethod
    def _source_node_id(source_name):
        return f"source::{source_name}"

    @staticmethod
    def _logger_node_id(yaml_file, logger_name):
        return f"logger::{yaml_file}::{logger_name}"

    @staticmethod
    def _destination_node_id(destination_value):
        return f"destination::{destination_value}"

    @property
    def _is_yed_format(self):
        return self.graphml_format == GRAPHML_FORMAT_YED

    @staticmethod
    def _add_yed_node_graphics(node, label, shape):
        data = ET.SubElement(node, "data", {"key": "node_graphics"})
        shape_node = ET.SubElement(data, f"{{{YFILES_NAMESPACE}}}ShapeNode")
        ET.SubElement(shape_node, f"{{{YFILES_NAMESPACE}}}Geometry", {"width": str(estimate_node_width(label)), "height": str(NODE_HEIGHT_PX)})
        ET.SubElement(shape_node, f"{{{YFILES_NAMESPACE}}}Shape", {"type": shape})
        ET.SubElement(shape_node, f"{{{YFILES_NAMESPACE}}}BorderStyle", {"type": "line", "width": "1.0", "color": CLASSIC_LIGHT.default_node_border_color})
        ET.SubElement(shape_node, f"{{{YFILES_NAMESPACE}}}NodeLabel", {"autoSizePolicy": "content"}).text = label

    @staticmethod
    def _add_generic_node_data(node, label, kind, group_label):
        ET.SubElement(node, "data", {"key": "label"}).text = label
        ET.SubElement(node, "data", {"key": "kind"}).text = kind
        ET.SubElement(node, "data", {"key": "group"}).text = group_label

    def _generate_node_xml(self, graph, node):
        node_element = ET.SubElement(graph, "node", {"id": node.node_id})
        if self._is_yed_format:
            self._add_yed_node_graphics(node_element, node.label, "roundrectangle")
        else:
            self._add_generic_node_data(node_element, node.label, node.kind, node.group_label)

    @staticmethod
    def _generate_yed_group_node_xml(graph, group_id, label, fill_color):
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

    def _generate_group_node_xml(self, graph, group_id, label, fill_color):
        """
        Returns the graph element that the group's member nodes belong in.

        Generic GraphML readers commonly drop nested graphs, so the generic format
        keeps members in the parent graph and records the group on each node instead.
        """
        if self._is_yed_format:
            return self._generate_yed_group_node_xml(graph, group_id, label, fill_color)
        return graph

    def _add_node_elements(self, graph):
        nodes_by_group_id = {}
        for node in self.nodes:
            nodes_by_group_id.setdefault(node.group_id, []).append(node)

        for group_index, (group_id, group_nodes) in enumerate(nodes_by_group_id.items()):
            group_graph = self._generate_group_node_xml(graph, group_id, group_nodes[0].group_label, CLASSIC_LIGHT.group_fill_color(group_index))
            for node in group_nodes:
                self._generate_node_xml(group_graph, node)

    @staticmethod
    def _add_yed_edge_graphics(edge):
        data = ET.SubElement(edge, "data", {"key": "edge_graphics"})
        polyline_edge = ET.SubElement(data, f"{{{YFILES_NAMESPACE}}}PolyLineEdge")
        ET.SubElement(polyline_edge, f"{{{YFILES_NAMESPACE}}}Arrows", {"source": "none", "target": "standard"})

    def _add_edge_elements(self, graph):
        for edge_index, edge in enumerate(self.edges):
            edge_element = ET.SubElement(graph, "edge", {"id": f"e{edge_index}", "source": edge.source_node_id, "target": edge.target_node_id})
            if self._is_yed_format:
                self._add_yed_edge_graphics(edge_element)

    def _add_key_elements(self, root):
        if self._is_yed_format:
            ET.SubElement(root, "key", {"for": "node", "id": "node_graphics", "yfiles.type": "nodegraphics"})
            ET.SubElement(root, "key", {"for": "edge", "id": "edge_graphics", "yfiles.type": "edgegraphics"})
            return
        for node_attribute_name in ("label", "kind", "group"):
            ET.SubElement(root, "key", {"for": "node", "id": node_attribute_name, "attr.name": node_attribute_name, "attr.type": "string"})

    def _build_root_element(self):
        schema_location = YED_SCHEMA_LOCATION if self._is_yed_format else GENERIC_SCHEMA_LOCATION
        root = ET.Element("graphml", {
            "xmlns": GRAPHML_NAMESPACE,
            "xmlns:xsi": XSI_NAMESPACE,
            "xsi:schemaLocation": f"{GRAPHML_NAMESPACE} {schema_location}",
        })
        self._add_key_elements(root)
        graph = ET.SubElement(root, "graph", {"id": "G", "edgedefault": "directed"})

        self._add_node_elements(graph)
        self._add_edge_elements(graph)

        ET.indent(root)
        return root

    def to_xml(self):
        root = self._build_root_element()
        return ET.tostring(root, encoding="unicode", xml_declaration=True)
