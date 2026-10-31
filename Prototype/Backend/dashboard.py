"""
dashboard.py — Aggregate summary for the landing page: entity counts,
risk-level distribution, the most-connected people, and the busiest
cases. Each figure is its own small, cheap query rather than one giant
query, since the dataset is small and this keeps each piece easy to
read and change independently.
"""

from __future__ import annotations

from db import run_query

_COUNT_QUERIES = {
    "persons": "MATCH (p:Person) RETURN count(p) AS count",
    "phones": "MATCH (ph:Phone) RETURN count(ph) AS count",
    "accounts": "MATCH (a:Account) RETURN count(a) AS count",
    "vehicles": "MATCH (v:Vehicle) RETURN count(v) AS count",
    "cases": "MATCH (c:Case) RETURN count(c) AS count",
    "calls": "MATCH ()-[r:CALLED]->() RETURN count(r) AS count",
    "transactions": "MATCH ()-[r:TRANSACTED_WITH]->() RETURN count(r) AS count",
}

_RISK_DISTRIBUTION_QUERY = """
MATCH (p:Person)
WHERE p.risk_level IS NOT NULL
RETURN p.risk_level AS risk_level, count(p) AS count
"""

_MOST_CONNECTED_QUERY = """
MATCH (p:Person)
OPTIONAL MATCH (p)-[r]-()
WITH p, count(DISTINCT r) AS degree
RETURN p.person_id AS person_id, p.name AS name, degree
ORDER BY degree DESC
LIMIT 5
"""

_BUSIEST_CASES_QUERY = """
MATCH (c:Case)
OPTIONAL MATCH (c)<-[:INVOLVED_IN]-(p:Person)
RETURN c.case_id AS case_id, c.description AS description, count(DISTINCT p) AS linked_person_count
ORDER BY linked_person_count DESC
LIMIT 5
"""


def get_dashboard_summary() -> dict:
    """
    Returns:
        {
          "counts": {persons, phones, accounts, vehicles, cases, calls, transactions},
          "risk_distribution": {"High": n, "Medium": n, "Low": n},  # 0 for any level with no scored persons
          "scored_person_count": int,   # how many persons have a risk_level at all
          "most_connected": [{person_id, name, degree}, ...],
          "busiest_cases": [{case_id, description, linked_person_count}, ...],
        }
    """
    counts = {key: run_query(q)[0]["count"] for key, q in _COUNT_QUERIES.items()}

    risk_rows = run_query(_RISK_DISTRIBUTION_QUERY)
    risk_distribution = {"High": 0, "Medium": 0, "Low": 0}
    for row in risk_rows:
        if row["risk_level"] in risk_distribution:
            risk_distribution[row["risk_level"]] = row["count"]
    scored_person_count = sum(risk_distribution.values())

    most_connected = run_query(_MOST_CONNECTED_QUERY)
    busiest_cases = run_query(_BUSIEST_CASES_QUERY)

    return {
        "counts": counts,
        "risk_distribution": risk_distribution,
        "scored_person_count": scored_person_count,
        "most_connected": most_connected,
        "busiest_cases": busiest_cases,
    }
