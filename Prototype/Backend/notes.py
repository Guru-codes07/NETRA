"""
notes.py — Free-text annotations ("notes") attachable to any node in the
graph: Person, Phone, Account, Vehicle, or Case.

Each note is its own (:Note {note_id, text, created_at}) node, linked to
the entity it annotates via an ANNOTATES relationship. This (rather than
a property on the target node) allows multiple notes per entity, each
with its own timestamp, and clean deletion of a single note without
touching the entity it's attached to.

Entity type is validated against a fixed whitelist before being used to
build a label in Cypher (labels can't be parameterized), so there is no
injection risk — only these five known labels are ever interpolated.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from db import run_query

# Maps each allowed entity type to its identifying property name.
ENTITY_ID_PROPERTY = {
    "Person": "person_id",
    "Phone": "phone_number",
    "Account": "account_id",
    "Vehicle": "plate_number",
    "Case": "case_id",
}


def _validate_entity_type(entity_type: str) -> str:
    if entity_type not in ENTITY_ID_PROPERTY:
        allowed = ", ".join(ENTITY_ID_PROPERTY)
        raise ValueError(f"Unknown entity_type '{entity_type}'. Must be one of: {allowed}")
    return ENTITY_ID_PROPERTY[entity_type]


def add_note(entity_type: str, entity_id: str, text: str) -> dict | None:
    """
    Attaches a new note to the given entity. Returns the created note, or
    None if no entity of that type/id exists. Raises ValueError for an
    unrecognized entity_type.
    """
    id_prop = _validate_entity_type(entity_type)
    note_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    query = f"""
    MATCH (target:{entity_type} {{{id_prop}: $entity_id}})
    CREATE (n:Note {{note_id: $note_id, text: $text, created_at: $created_at}})-[:ANNOTATES]->(target)
    RETURN n.note_id AS note_id, n.text AS text, n.created_at AS created_at
    """
    result = run_query(query, {
        "entity_id": entity_id,
        "note_id": note_id,
        "text": text,
        "created_at": created_at,
    })
    return result[0] if result else None


def get_notes(entity_type: str, entity_id: str) -> list[dict]:
    """Every note attached to the given entity, newest first. Raises ValueError for an unrecognized entity_type."""
    id_prop = _validate_entity_type(entity_type)

    query = f"""
    MATCH (target:{entity_type} {{{id_prop}: $entity_id}})<-[:ANNOTATES]-(n:Note)
    RETURN n.note_id AS note_id, n.text AS text, n.created_at AS created_at
    ORDER BY n.created_at DESC
    """
    return run_query(query, {"entity_id": entity_id})


def delete_note(note_id: str) -> bool:
    """Deletes a single note by its id. Returns True if a note was found and deleted, False otherwise."""
    query = """
    MATCH (n:Note {note_id: $note_id})
    WITH n, count(n) AS found
    DETACH DELETE n
    RETURN found
    """
    result = run_query(query, {"note_id": note_id})
    return bool(result and result[0]["found"] > 0)
