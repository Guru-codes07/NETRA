"""
watchlist.py — Lets an investigator flag specific people so they stay
highlighted in every graph view, regardless of how that view was reached
(search, network traversal, cluster detection, case view).

Implementation: a plain boolean property `on_watchlist` written onto the
Person node itself (same pattern as risk_score/risk_level in risk.py).
Because it lives on the node, every existing endpoint that returns Person
nodes picks it up automatically — no per-endpoint changes needed. The
frontend just needs to read `properties.on_watchlist` wherever it already
reads `properties.risk_level`, and style accordingly.
"""

from __future__ import annotations

from db import run_query

_ADD_QUERY = """
MATCH (p:Person {person_id: $person_id})
SET p.on_watchlist = true
RETURN p.person_id AS person_id, p.name AS name, p.on_watchlist AS on_watchlist
"""

_REMOVE_QUERY = """
MATCH (p:Person {person_id: $person_id})
SET p.on_watchlist = false
RETURN p.person_id AS person_id, p.name AS name, p.on_watchlist AS on_watchlist
"""

_LIST_QUERY = """
MATCH (p:Person {on_watchlist: true})
RETURN p.person_id AS person_id, p.name AS name, p.city AS city,
       p.risk_score AS risk_score, p.risk_level AS risk_level
ORDER BY p.name
"""


def add_to_watchlist(person_id: str) -> dict | None:
    """Flags a person as watchlisted. Returns the updated record, or None if no such person exists."""
    result = run_query(_ADD_QUERY, {"person_id": person_id})
    return result[0] if result else None


def remove_from_watchlist(person_id: str) -> dict | None:
    """Un-flags a person. Returns the updated record, or None if no such person exists."""
    result = run_query(_REMOVE_QUERY, {"person_id": person_id})
    return result[0] if result else None


def get_watchlist() -> list[dict]:
    """Every currently watchlisted person, alphabetical by name."""
    return run_query(_LIST_QUERY)
