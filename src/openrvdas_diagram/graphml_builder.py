import xml.etree.ElementTree as ET

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
    Calculate correct node width based on the label.

    yEd doesn't grow a node to fit its label on its own.  The Geometry we emit
    is the only thing that gives the label room, so it has to be sized up front.
    """
    return max(NODE_MIN_WIDTH_PX, len(label) * NODE_LABEL_CHAR_WIDTH_PX)


openrvdas_remote_writer_classes = {
    #TODO: add default behavior to handle openrvdas classes that arent listed here
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
    #TODO: add default behavior to handle openrvdas classes that arent listed here
    "FileWriter",
    "TextFileWriter",
    "LogfileWriter",
    "RegexLogfileWriter",
    "RecordScreenWriter",
}

class GraphmlBuilder:
    """Builds a GraphML data-flow diagram from the logger inventory returned by
    LoggerInventoryBuilder.

    graphml_format selects who the output is compatible with:
        - "yed": styled nodes nested inside yEd group nodes.
        - "generic": standard GraphML only.  Nodes are flat and unstyled, and
          describe themselves with label, kind and group data attributes.

    The yEd output always uses the classic colors; color schemes are chosen when
    rendering generic GraphML with GraphmlRenderer.
    """

    def __init__(self, inventory, graphml_format=GRAPHML_FORMAT_YED):
        if graphml_format not in SUPPORTED_GRAPHML_FORMATS:
            raise ValueError(
                f"unknown graphml format: {graphml_format!r}, expected one of {SUPPORTED_GRAPHML_FORMATS}"
            )

        self.inventory = inventory
        self.graphml_format = graphml_format

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
        #TODO: handle N number of loggers instead of logger_1 and logger_2
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

    def _generate_node_xml(self, graph, node_id, label, shape, kind, group_label):
        node = ET.SubElement(graph, "node", {"id": node_id})
        if self._is_yed_format:
            self._add_yed_node_graphics(node, label, shape)
        else:
            self._add_generic_node_data(node, label, kind, group_label)

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
        group_index = 0

        sources_group_label = "sources"
        sources_graph = self._generate_group_node_xml(graph, "group_sources", sources_group_label, CLASSIC_LIGHT.group_fill_color(group_index))
        group_index += 1
        for source_name in self.nodes["sources"]:
            self._generate_node_xml(
                sources_graph,
                self._source_node_id(source_name),
                source_name,
                "roundrectangle",
                "source",
                sources_group_label,
            )

        for yaml_file, logger_definitions in self.nodes["loggers"].items():
            loggers_graph = self._generate_group_node_xml(graph, f"group_loggers::{yaml_file}", yaml_file, CLASSIC_LIGHT.group_fill_color(group_index))
            group_index += 1
            for logger_name in logger_definitions:
                self._generate_node_xml(loggers_graph, self._logger_node_id(yaml_file, logger_name), logger_name, "roundrectangle", "logger", yaml_file)

        destinations_group_label = "destinations"
        destinations_graph = self._generate_group_node_xml(graph, "group_destinations", destinations_group_label, CLASSIC_LIGHT.group_fill_color(group_index))
        group_index += 1
        for destination_value in self.nodes["destinations"]:
            self._generate_node_xml(destinations_graph, self._destination_node_id(destination_value), destination_value, "roundrectangle", "destination", destinations_group_label)

    @staticmethod
    def _add_yed_edge_graphics(edge):
        data = ET.SubElement(edge, "data", {"key": "edge_graphics"})
        polyline_edge = ET.SubElement(data, f"{{{YFILES_NAMESPACE}}}PolyLineEdge")
        ET.SubElement(polyline_edge, f"{{{YFILES_NAMESPACE}}}Arrows", {"source": "none", "target": "standard"})

    @staticmethod
    def _add_generic_edge_data(edge, kind):
        ET.SubElement(edge, "data", {"key": "edge_kind"}).text = kind

    def _add_edge_elements(self, graph):
        for edge_index, (from_id, to_id, kind) in enumerate(self.edges):
            source_id, target_id = self._edge_endpoint_ids(from_id, to_id, kind)
            edge = ET.SubElement(graph, "edge", {"id": f"e{edge_index}", "source": source_id, "target": target_id})
            if self._is_yed_format:
                self._add_yed_edge_graphics(edge)
            else:
                self._add_generic_edge_data(edge, kind)

    def _add_key_elements(self, root):
        if self._is_yed_format:
            ET.SubElement(root, "key", {"for": "node", "id": "node_graphics", "yfiles.type": "nodegraphics"})
            ET.SubElement(root, "key", {"for": "edge", "id": "edge_graphics", "yfiles.type": "edgegraphics"})
            return
        for node_attribute_name in ("label", "kind", "group"):
            ET.SubElement(root, "key", {"for": "node", "id": node_attribute_name, "attr.name": node_attribute_name, "attr.type": "string"})
        ET.SubElement(root, "key", {"for": "edge", "id": "edge_kind", "attr.name": "kind", "attr.type": "string"})

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
