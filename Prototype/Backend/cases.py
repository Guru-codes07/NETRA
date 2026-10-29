"""
cases.py — Case view queries: list all cases, and drill into one case to
see every linked person (with risk score, if computed) plus the phones,
accounts, and vehicles those persons own.

Note on "evidence": the current dataset has no dedicated evidence entity —
only Person, Phone, Account, Vehicle, and Case. So "linked entities" here
(each person's owned phones/accounts/vehicles) stands in as the closest
available proxy for case evidence. This is documented explicitly rather
than inventing data that isn't in the schema.
"""

from __future__ import annotations

from db import run_query

_ALL_CASES_QUERY = """
MATCH (c:Case)
OPTIONAL MATCH (c)<-[:INVOLVED_IN]-(p:Person)
RETURN c.case_id AS case_id,
       c.description AS description,
       c.location AS location,
       count(DISTINCT p) AS linked_person_count
ORDER BY c.case_id
"""

_CASE_EXISTS_QUERY = "MATCH (c:Case {case_id: $case_id}) RETURN c.case_id AS id"

_CASE_PERSONS_QUERY = """
MATCH (c:Case {case_id: $case_id})<-[:INVOLVED_IN]-(p:Person)
RETURN p.person_id AS person_id,
       p.name AS name,
       p.age AS age,
       p.gender AS gender,
       p.city AS city,
       p.risk_score AS risk_score,
       p.risk_level AS risk_level
ORDER BY coalesce(p.risk_score, -1) DESC, p.name
"""

_CASE_LINKED_ENTITIES_QUERY = """
MATCH (c:Case {case_id: $case_id})<-[:INVOLVED_IN]-(p:Person)-[:OWNS]->(e)
RETURN p.person_id AS person_id,
       p.name AS person_name,
       labels(e)[0] AS entity_type,
       coalesce(e.phone_number, e.account_id, e.plate_number) AS entity_id,
       coalesce(e.bank_name, e.vehicle_type, '') AS entity_detail
ORDER BY p.name, entity_type
"""


def get_all_cases() -> list[dict]:
    """One row per case: id, description, location, and how many people are linked to it."""
    return run_query(_ALL_CASES_QUERY)


def get_case_detail(case_id: str) -> dict | None:
    """
    Full case detail: the case's own fields, every linked person (sorted
    highest-risk first, if risk scores have been computed), and the
    phones/accounts/vehicles those persons own as a proxy for evidence.

    Returns None if no case with this id exists.
    """
    exists = run_query(_CASE_EXISTS_QUERY, {"case_id": case_id})
    if not exists:
        return None

    cases = run_query(
        "MATCH (c:Case {case_id: $case_id}) RETURN c.case_id AS case_id, c.description AS description, c.location AS location",
        {"case_id": case_id},
    )
    case_info = cases[0]

    persons = run_query(_CASE_PERSONS_QUERY, {"case_id": case_id})
    linked_entities = run_query(_CASE_LINKED_ENTITIES_QUERY, {"case_id": case_id})

    return {
        **case_info,
        "persons": persons,
        "linked_entities": linked_entities,
    }
