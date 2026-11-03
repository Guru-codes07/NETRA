"""
timeline.py — Combined call + transaction timeline for a single person.

Pulls every CALLED event on that person's phones and every
TRANSACTED_WITH event on their accounts, merges both into one
chronologically-sorted list. Used by GET /person/{person_id}/timeline.
"""

from __future__ import annotations

from db import run_query

_PERSON_EXISTS_QUERY = "MATCH (p:Person {person_id: $person_id}) RETURN p.person_id AS id"

_CALLS_QUERY = """
MATCH (p:Person {person_id: $person_id})-[:OWNS]->(ph:Phone)-[c:CALLED]-(other:Phone)
RETURN c.timestamp AS timestamp,
       'call' AS event_type,
       ph.phone_number AS self_entity,
       other.phone_number AS counterparty,
       c.duration_seconds AS duration_seconds,
       null AS amount
"""

_TRANSACTIONS_QUERY = """
MATCH (p:Person {person_id: $person_id})-[:OWNS]->(a:Account)-[t:TRANSACTED_WITH]-(other:Account)
RETURN t.timestamp AS timestamp,
       'transaction' AS event_type,
       a.account_id AS self_entity,
       other.account_id AS counterparty,
       null AS duration_seconds,
       t.amount AS amount
"""


def get_person_timeline(person_id: str) -> list[dict] | None:
    """
    Returns a chronologically-sorted list of call and transaction events
    involving the given person, or None if no such person exists.

    Each event: {timestamp, event_type, self_entity, counterparty, duration_seconds, amount}
    `duration_seconds` is only set for calls, `amount` only for transactions.
    """
    exists = run_query(_PERSON_EXISTS_QUERY, {"person_id": person_id})
    if not exists:
        return None

    calls = run_query(_CALLS_QUERY, {"person_id": person_id})
    transactions = run_query(_TRANSACTIONS_QUERY, {"person_id": person_id})

    events = calls + transactions
    # Timestamps are stored as ISO-like strings (e.g. "2026-04-18 01:26:15.628707"),
    # which sort correctly as plain strings without parsing.
    events.sort(key=lambda e: e["timestamp"] or "")
    return events
