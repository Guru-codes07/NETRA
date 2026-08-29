"""
graph_utils.py — convert raw Neo4j Node/Relationship objects into the
{nodes: [...], edges: [...]} JSON shape the frontend (Cytoscape.js etc.)
expects, with de-duplication across many rows/paths.
"""


def node_to_dict(node):
    """Convert a neo4j.graph.Node into a plain JSON-safe dict."""
    props = dict(node)
    label = list(node.labels)[0] if node.labels else "Unknown"
    return {
        "id": node.element_id,
        "type": label,
        "properties": props,
        # a human-friendly display label for the frontend graph view
        "display": (
            props.get("name")
            or props.get("phone_number")
            or props.get("account_id")
            or props.get("plate_number")
            or props.get("case_id")
            or props.get("person_id")
            or label
        ),
    }


def rel_to_dict(rel):
    """Convert a neo4j.graph.Relationship into a plain JSON-safe dict."""
    return {
        "id": rel.element_id,
        "type": rel.type,
        "source": rel.start_node.element_id,
        "target": rel.end_node.element_id,
        "properties": dict(rel),
    }


class GraphAccumulator:
    """
    Collects nodes/relationships across many query rows or paths,
    de-duplicating by element_id, and exports the final {nodes, edges} JSON.
    """

    def __init__(self):
        self._nodes = {}
        self._edges = {}

    def add_node(self, node):
        if node is None:
            return
        d = node_to_dict(node)
        self._nodes[d["id"]] = d

    def add_rel(self, rel):
        if rel is None:
            return
        d = rel_to_dict(rel)
        self._edges[d["id"]] = d
        # make sure both endpoints are captured too
        self.add_node(rel.start_node)
        self.add_node(rel.end_node)

    def add_path(self, path):
        """Add every node and relationship in a neo4j.graph.Path."""
        if path is None:
            return
        for node in path.nodes:
            self.add_node(node)
        for rel in path.relationships:
            self.add_rel(rel)

    def to_json(self):
        return {
            "nodes": list(self._nodes.values()),
            "edges": list(self._edges.values()),
        }
