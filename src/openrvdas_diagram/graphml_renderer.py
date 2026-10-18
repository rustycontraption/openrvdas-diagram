import html
import json
import xml.etree.ElementTree as ET

import graphviz

from openrvdas_diagram.color_schemes import CLASSIC_LIGHT, DEFAULT_BACKGROUND_COLOR
from openrvdas_diagram.graphml_builder import GRAPHML_NAMESPACE

'''
Assumptions:
    - The GraphML was written by GraphmlBuilder in the generic format
    - Nodes with the same group value belong in the same group box
    - All colors come from the ColorScheme passed in (classic by default)
    - Groups are colored in the order they first appear, which matches the yEd output
    - An edge is identified by eye from its color, which it shares with the source it
      leaves or the destination it arrives at
    - Every edge gets its own attachment point, spaced along the side of the node
'''

REQUIRED_NODE_DATA_KEYS = ("label", "kind", "group")
# Loggers sit between a colored source and a colored destination, so stay neutral
COLORED_NODE_KINDS = ("source", "destination")

RANK_DIRECTION = "LR"
RANK_SEPARATION_INCHES = "2.5"
NODE_SEPARATION_INCHES = "0.35"
EDGE_ROUTING = "spline"
FONT_NAME = "Helvetica"
# Nodes are drawn by their HTML table label, so the Graphviz shape itself is invisible
NODE_SHAPE = "plain"
NODE_BORDER_WIDTH = "1"
NODE_LABEL_PADDING_POINTS = "8"
EDGE_PORT_SPACING_POINTS = "7"
GROUP_STYLE = "rounded,filled"
EDGE_ARROWHEAD = "normal"
EDGE_LINE_WIDTH = "1.5"
# Edges leave and enter on the sides that face the next layer for RANK_DIRECTION
EDGE_TAIL_SIDE = "e"
EDGE_HEAD_SIDE = "w"

COLORED_NODE_BORDER_WIDTH = "3"
# DOT output is drawn as SVG on whatever page shows it, so it has no background of its own;
# Graphviz would otherwise paint a white rectangle behind it
TRANSPARENT_BACKGROUND = "transparent"


class GraphmlRenderer:
    """Renders the generic GraphML written by GraphmlBuilder as a PNG, laid out
    in layers with Graphviz dot, in the colors of color_scheme."""

    def __init__(self, graphml_text, color_scheme=CLASSIC_LIGHT):
        self.root = ET.fromstring(graphml_text)
        self.color_scheme = color_scheme

        self.nodes = []
        self.edges = []

        self._reject_yed_format()
        self._parse_nodes()
        self._parse_edges()

    def _find_all(self, tag_name):
        return self.root.findall(f".//{{{GRAPHML_NAMESPACE}}}{tag_name}")

    def _reject_yed_format(self):
        if any("yfiles.type" in key.attrib for key in self._find_all("key")):
            raise ValueError(
                "this is yEd-format GraphML, regenerate it with --graphml-format generic"
            )

    @staticmethod
    def _read_data(element):
        return {data.get("key"): data.text or "" for data in element.findall(f"{{{GRAPHML_NAMESPACE}}}data")}

    def _parse_nodes(self):
        for node_element in self._find_all("node"):
            node_id = node_element.get("id")
            node_data = self._read_data(node_element)
            missing_keys = [key for key in REQUIRED_NODE_DATA_KEYS if key not in node_data]
            if missing_keys:
                raise ValueError(
                    f"node {node_id!r} is missing data {missing_keys}, "
                    "expected GraphML generated with --graphml-format generic"
                )
            self.nodes.append({"id": node_id, **{key: node_data[key] for key in REQUIRED_NODE_DATA_KEYS}})

    def _parse_edges(self):
        known_node_ids = {node["id"] for node in self.nodes}
        for edge_element in self._find_all("edge"):
            source_id, target_id = edge_element.get("source"), edge_element.get("target")
            for endpoint_id in (source_id, target_id):
                if endpoint_id not in known_node_ids:
                    raise ValueError(f"edge refers to unknown node {endpoint_id!r}")
            self.edges.append((source_id, target_id))

    def _nodes_by_group(self):
        nodes_by_group = {}
        for node in self.nodes:
            nodes_by_group.setdefault(node["group"], []).append(node)
        return nodes_by_group

    def _dot_node_names(self):
        """
        Maps each GraphML node id to a name that is safe to use in DOT.

        Our GraphML ids contain colons, which DOT reads as a node:port separator.
        """
        return {node["id"]: f"node_{node_index}" for node_index, node in enumerate(self.nodes)}

    def _node_colors(self):
        colored_nodes = [node for node in self.nodes if node["kind"] in COLORED_NODE_KINDS]
        return {
            node["id"]: self.color_scheme.node_color(colored_node_index)
            for colored_node_index, node in enumerate(colored_nodes)
        }

    def _declared_node_order(self):
        return {node["id"]: node_index for node_index, node in enumerate(self.nodes)}

    def _edge_port_indexes(self, node_order):
        """
        Gives every edge its own port on its tail node and on its head node.

        Ports run down the side of a node.  An edge takes a port in the order of
        where its other end sits in node_order, so the edges of one node fan out
        without crossing each other.  Returns (tail_port_index, head_port_index)
        for each edge, in the same order as self.edges.
        """
        outgoing_edge_indexes, incoming_edge_indexes = {}, {}
        for edge_index, (source_id, target_id) in enumerate(self.edges):
            outgoing_edge_indexes.setdefault(source_id, []).append(edge_index)
            incoming_edge_indexes.setdefault(target_id, []).append(edge_index)

        tail_port_indexes, head_port_indexes = {}, {}
        for edge_indexes in outgoing_edge_indexes.values():
            edge_indexes.sort(key=lambda edge_index: (node_order[self.edges[edge_index][1]], edge_index))
            tail_port_indexes.update({edge_index: port_index for port_index, edge_index in enumerate(edge_indexes)})
        for edge_indexes in incoming_edge_indexes.values():
            edge_indexes.sort(key=lambda edge_index: (node_order[self.edges[edge_index][0]], edge_index))
            head_port_indexes.update({edge_index: port_index for port_index, edge_index in enumerate(edge_indexes)})

        return [(tail_port_indexes[edge_index], head_port_indexes[edge_index]) for edge_index in range(len(self.edges))]

    @staticmethod
    def _port_column_html(port_prefix, port_count):
        if port_count == 0:
            return '<TD WIDTH="1"></TD>'
        port_rows = "".join(
            f'<TR><TD PORT="{port_prefix}_{port_index}" FIXEDSIZE="TRUE" WIDTH="1" HEIGHT="{EDGE_PORT_SPACING_POINTS}"></TD></TR>'
            for port_index in range(port_count)
        )
        return f'<TD><TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="0">{port_rows}</TABLE></TD>'

    def _node_label_html(self, label, incoming_port_count, outgoing_port_count, border_color, border_width):
        """
        Draws a node as a rounded box with a column of incoming edge ports down
        one side and a column of outgoing edge ports down the other.
        """
        return (
            f'<<TABLE BORDER="{border_width}" COLOR="{border_color}" BGCOLOR="{self.color_scheme.node_fill_color}" STYLE="ROUNDED" '
            f'CELLBORDER="0" CELLSPACING="0" CELLPADDING="0"><TR>'
            f'{self._port_column_html("in", incoming_port_count)}'
            f'<TD CELLPADDING="{NODE_LABEL_PADDING_POINTS}">{html.escape(label)}</TD>'
            f'{self._port_column_html("out", outgoing_port_count)}'
            f'</TR></TABLE>>'
        )

    def _build_digraph(self, node_order, background_color):
        dot_node_names = self._dot_node_names()
        node_colors = self._node_colors()
        edge_port_indexes = self._edge_port_indexes(node_order)

        incoming_port_counts, outgoing_port_counts = {}, {}
        for source_id, target_id in self.edges:
            outgoing_port_counts[source_id] = outgoing_port_counts.get(source_id, 0) + 1
            incoming_port_counts[target_id] = incoming_port_counts.get(target_id, 0) + 1

        color_scheme = self.color_scheme
        graph_attributes = {
            "rankdir": RANK_DIRECTION,
            "ranksep": RANK_SEPARATION_INCHES,
            "nodesep": NODE_SEPARATION_INCHES,
            "splines": EDGE_ROUTING,
            "fontname": FONT_NAME,
            "bgcolor": background_color,
        }
        node_attributes = {"shape": NODE_SHAPE, "fontname": FONT_NAME}
        # Left unset when the scheme has no preference, so Graphviz uses its default
        if color_scheme.text_color:
            graph_attributes["fontcolor"] = color_scheme.text_color
            node_attributes["fontcolor"] = color_scheme.text_color

        digraph = graphviz.Digraph(
            graph_attr=graph_attributes,
            node_attr=node_attributes,
            edge_attr={
                "arrowhead": EDGE_ARROWHEAD,
                "penwidth": EDGE_LINE_WIDTH,
                "color": color_scheme.default_edge_color,
            },
        )

        for group_index, (group_label, group_nodes) in enumerate(self._nodes_by_group().items()):
            group_color = color_scheme.group_fill_color(group_index)
            with digraph.subgraph(name=f"cluster_{group_index}") as group_cluster:
                group_cluster.attr(label=group_label, style=GROUP_STYLE, fillcolor=group_color, color=group_color)
                for node in group_nodes:
                    is_colored = node["id"] in node_colors
                    group_cluster.node(
                        dot_node_names[node["id"]],
                        label=self._node_label_html(
                            node["label"],
                            incoming_port_counts.get(node["id"], 0),
                            outgoing_port_counts.get(node["id"], 0),
                            node_colors[node["id"]] if is_colored else color_scheme.default_node_border_color,
                            COLORED_NODE_BORDER_WIDTH if is_colored else NODE_BORDER_WIDTH,
                        ),
                    )

        for (source_id, target_id), (tail_port_index, head_port_index) in zip(self.edges, edge_port_indexes):
            edge_color = node_colors.get(source_id) or node_colors.get(target_id) or color_scheme.default_edge_color
            digraph.edge(
                f"{dot_node_names[source_id]}:out_{tail_port_index}:{EDGE_TAIL_SIDE}",
                f"{dot_node_names[target_id]}:in_{head_port_index}:{EDGE_HEAD_SIDE}",
                color=edge_color,
            )

        return digraph

    def _laid_out_node_order(self):
        """
        Asks Graphviz where it places each node, and returns the nodes ranked from
        the top of the picture to the bottom.

        Ports can only be handed out in a crossing-free order once the node
        positions are known, so the layout is run once to measure and once to draw.
        """
        layout_digraph = self._build_digraph(self._declared_node_order(), TRANSPARENT_BACKGROUND)
        layout = json.loads(layout_digraph.pipe(format="json"))
        vertical_positions = {
            layout_object["name"]: float(layout_object["pos"].split(",")[1])
            for layout_object in layout.get("objects", [])
            if "pos" in layout_object
        }
        dot_node_names = self._dot_node_names()
        # Graphviz measures upward from the bottom, so the highest position comes first
        return {node["id"]: -vertical_positions[dot_node_names[node["id"]]] for node in self.nodes}

    def to_dot(self):
        """DOT source with ports in declared node order and a transparent background,
        which needs no Graphviz install.  to_png refines the port order from the
        measured layout."""
        return self._build_digraph(self._declared_node_order(), TRANSPARENT_BACKGROUND).source

    def _png_background_color(self):
        return self.color_scheme.background_color or DEFAULT_BACKGROUND_COLOR

    def to_png(self):
        """A PNG drawn on the color scheme's background, white if the scheme has none."""
        return self._build_digraph(self._laid_out_node_order(), self._png_background_color()).pipe(format="png")
