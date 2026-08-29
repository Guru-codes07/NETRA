"""

NETRA - Network entity tracking and relationship analysis.
db.py — Neo4j driver connection for NETRA backend.


Keeps a single shared driver instance for the whole FastAPI app,
opened at startup and closed at shutdown (see main.py lifespan).
"""

from neo4j import GraphDatabase

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password123"

_driver = None


def get_driver():
    """Return the shared Neo4j driver, creating it on first call."""
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    return _driver


def close_driver():
    """Close the shared driver cleanly on app shutdown."""
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


def run_query(query: str, parameters: dict | None = None):
    """
    Run a Cypher query and return a list of plain dict records
    (nodes/relationships flattened to plain property dicts).
    Use this for simple property-only results.
    """
    driver = get_driver()
    with driver.session() as session:
        result = session.run(query, parameters or {})
        return [record.data() for record in result]


def run_raw(query: str, parameters: dict | None = None):
    """
    Run a Cypher query and return the raw records (list), fully consumed
    within the session. Use this when you need actual Node/Relationship
    graph objects (element_id, labels, type) rather than flattened dicts —
    e.g. for building nodes/edges graph JSON for the frontend.
    """
    driver = get_driver()
    with driver.session() as session:
        result = session.run(query, parameters or {})
        return list(result)
