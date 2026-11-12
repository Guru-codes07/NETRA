"""
paths.py — Shortest-path finder: "How is Person A linked to Person B?"

Uses Neo4j's built-in shortestPath() over the connection types that
actually link people in this graph:

    OWNS, INVOLVED_IN  — a person to a phone/account/vehicle/case
    CALLED             — phone to phone (call records)
    TRANSACTED_WITH    — account to account (transactions)

A chain can therefore run through shared entities (A owns a phone that
was involved in a case that B is also in) or through activity (A's phone
called a phone owned by B). The result is returned both as graph JSON
(nodes/edges, for drawing) and as an ordered list of human-readable steps
(for the sidebar).

Search depth is capped (MAX_HOPS) so an unlucky pair cannot make the
traversal explode on a larger graph.
"""

from __future__ import annotations

from db import run_query, run_raw
from graph_utils import GraphAccumulator, node_to_dict

MAX_HOPS = 10

_PATH_QUERY = f"""
MATCH (a:Person {{person_id: $from_id}}), (b:Person {{person_id: $to_id}})
MATCH p = shortestPath((a)-[:OWNS|INVOLVED_IN|CALLED|TRANSACTED_WITH*..{MAX_HOPS}]-(b))
RETURN p
"""

_PERSON_EXISTS_QUERY = "MATCH (p:Person {person_id: $person_id}) RETURN p.person_id AS id"


def _describe(node_dict: dict) -> str:
    """Short label for a node in a step description."""
    return node_dict.get("display") or node_dict.get("type", "entity")


def find_shortest_path(from_id: str, to_id: str) -> dict | None:
    """
    Returns None if either person doesn't exist. Otherwise returns:

        {
          "from_person_id", "to_person_id",
          "found": bool,
          "hops": int | None,           # number of relationships in the chain
          "steps": [ {from, from_type, relationship, to, to_type}, ... ],
          "graph": {"nodes": [...], "edges": [...]},
          "person_ids": [...],           # every Person on the chain, in order
        }

    found=False means both people exist but no chain exists between them
    within MAX_HOPS.
    """
    if not run_query(_PERSON_EXISTS_QUERY, {"person_id": from_id}):
        return None
    if not run_query(_PERSON_EXISTS_QUERY, {"person_id": to_id}):
        return None

    base = {"from_person_id": from_id, "to_person_id": to_id}

    if from_id == to_id:
        return {
            **base,
            "found": True,
            "hops": 0,
            "steps": [],
            "graph": {"nodes": [], "edges": []},
            "person_ids": [from_id],
        }

    records = run_raw(_PATH_QUERY, {"from_id": from_id, "to_id": to_id})
    if not records:
        return {**base, "found": False, "hops": None, "steps": [], "graph": {"nodes": [], "edges": []}, "person_ids": []}

    path = records[0]["p"]

    acc = GraphAccumulator()
    acc.add_path(path)

    # Walk the path in traversal order: nodes[i] --relationships[i]--> nodes[i+1]
    # The relationship's own start/end may be reversed relative to the walk,
    # so the step is described in walk order, not stored-direction order.
    node_dicts = [node_to_dict(n) for n in path.nodes]
    steps = []
    for i, rel in enumerate(path.relationships):
        a, b = node_dicts[i], node_dicts[i + 1]
        steps.append({
            "from": _describe(a),
            "from_type": a["type"],
            "relationship": rel.type,
            "to": _describe(b),
            "to_type": b["type"],
        })

    person_ids = [
        n["properties"]["person_id"]
        for n in node_dicts
        if n["type"] == "Person" and "person_id" in n["properties"]
    ]

    return {
        **base,
        "found": True,
        "hops": len(path.relationships),
        "steps": steps,
        "graph": acc.to_json(),
        "person_ids": person_ids,
    }
