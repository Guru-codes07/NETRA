"""
risk.py — Risk scoring engine for NETRA.

Scores every Person 0-100 based on graph structure, no manual labeling
required. The score is a blend of:

  - how connected they are (degree: phones, accounts, vehicles, cases)
  - how many cases they're tied to
  - how risky the people directly connected to them are (guilt-by-association,
    one hop only — a risky neighbor raises your own score a bit)

    final_score = (0.7 * own_score + 0.3 * avg_neighbor_own_score) * 100

`compute_all_risk_scores()` is the single source of truth — it always
recomputes across the whole graph so scores stay normalized relative to
everyone else, then writes risk_score/risk_level back onto every Person
node in Neo4j. Both the "precompute all" and "look up one person" API
endpoints call it; the dataset is small (hackathon/portfolio scale), so
recomputing the full graph on every call is fast and keeps scores
consistent rather than drifting out of sync.
"""

from __future__ import annotations

from db import run_query

# Score >= this is "High" risk, >= the lower bound is "Medium", else "Low".
HIGH_RISK_THRESHOLD = 66
MEDIUM_RISK_THRESHOLD = 33

# How much a person's own connections/cases count vs. their neighbors'.
OWN_WEIGHT = 0.7
NEIGHBOR_WEIGHT = 0.3


def _risk_level(score: float) -> str:
    if score >= HIGH_RISK_THRESHOLD:
        return "High"
    if score >= MEDIUM_RISK_THRESHOLD:
        return "Medium"
    return "Low"


def _fetch_person_stats() -> list[dict]:
    """One row per person: their degree (total direct relationships) and case count."""
    query = """
    MATCH (p:Person)
    OPTIONAL MATCH (p)-[r]-()
    WITH p, count(DISTINCT r) AS degree
    OPTIONAL MATCH (p)-[:INVOLVED_IN]->(c:Case)
    WITH p, degree, count(DISTINCT c) AS case_count
    RETURN p.person_id AS person_id, p.name AS name, degree, case_count
    """
    return run_query(query)


def _fetch_person_adjacency() -> dict[str, set[str]]:
    """
    person_id -> set of other person_ids they're directly linked to via a
    shared phone, account, vehicle, or case (one hop through a shared entity).
    """
    query = """
    MATCH (p:Person)-[:OWNS|INVOLVED_IN]-(shared)-[:OWNS|INVOLVED_IN]-(other:Person)
    WHERE p.person_id <> other.person_id
    RETURN p.person_id AS person_id, collect(DISTINCT other.person_id) AS neighbors
    """
    rows = run_query(query)
    return {row["person_id"]: set(row["neighbors"]) for row in rows}


def compute_all_risk_scores() -> list[dict]:
    """
    Compute a risk score for every person in the graph, persist it onto
    each Person node (risk_score, risk_level), and return the full list
    sorted highest-risk first.

    Returns: [{person_id, name, risk_score, risk_level, degree, case_count}, ...]
    """
    stats = _fetch_person_stats()
    if not stats:
        return []

    adjacency = _fetch_person_adjacency()

    max_degree = max((s["degree"] for s in stats), default=0) or 1
    max_cases = max((s["case_count"] for s in stats), default=0) or 1

    # Pass 1: each person's "own" score (0-1), from their own degree + cases.
    own_scores: dict[str, float] = {}
    for s in stats:
        degree_norm = s["degree"] / max_degree
        case_norm = s["case_count"] / max_cases
        own_scores[s["person_id"]] = (degree_norm * 0.5) + (case_norm * 0.5)

    # Pass 2: blend in the average own-score of directly connected persons.
    results = []
    for s in stats:
        pid = s["person_id"]
        own = own_scores[pid]
        neighbor_ids = adjacency.get(pid, set())
        if neighbor_ids:
            neighbor_avg = sum(own_scores.get(n, 0.0) for n in neighbor_ids) / len(neighbor_ids)
        else:
            neighbor_avg = 0.0

        final = (OWN_WEIGHT * own) + (NEIGHBOR_WEIGHT * neighbor_avg)
        score_100 = round(final * 100, 1)

        results.append({
            "person_id": pid,
            "name": s["name"],
            "risk_score": score_100,
            "risk_level": _risk_level(score_100),
            "degree": s["degree"],
            "case_count": s["case_count"],
        })

    _persist_risk_scores(results)
    results.sort(key=lambda r: r["risk_score"], reverse=True)
    return results


def _persist_risk_scores(results: list[dict]) -> None:
    """Write risk_score + risk_level onto each Person node in one batched query."""
    if not results:
        return
    query = """
    UNWIND $rows AS row
    MATCH (p:Person {person_id: row.person_id})
    SET p.risk_score = row.risk_score, p.risk_level = row.risk_level
    """
    rows = [{"person_id": r["person_id"], "risk_score": r["risk_score"], "risk_level": r["risk_level"]} for r in results]
    run_query(query, {"rows": rows})


def get_person_risk(person_id: str) -> dict | None:
    """Recompute all scores (cheap at this scale) and return just this person's entry, or None if not found."""
    all_scores = compute_all_risk_scores()
    for entry in all_scores:
        if entry["person_id"] == person_id:
            return entry
    return None
