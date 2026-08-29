"""
main.py — NETRA backend API.

Exposes the criminal-network graph (stored in Neo4j) over HTTP so a
frontend (React + Cytoscape.js, or anything else) can query and
visualize it.

"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from db import run_raw, run_query, close_driver
from graph_utils import GraphAccumulator
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Driver is created lazily on first use (see db.get_driver),
    # nothing needed on startup. Close it cleanly on shutdown.
    yield
    close_driver()

app = FastAPI(title="NETRA API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health_check():
    return {"status": "NETRA API running"}


@app.get("/person/{person_id}")
def get_person(person_id: str):
    """
    Return a person's own details plus everything they directly own or
    are involved in — phones, accounts, vehicles, cases — as nodes/edges
    JSON ready for graph visualization.
    """
    query = """
    MATCH (p:Person {person_id: $person_id})
    OPTIONAL MATCH (p)-[r]-(x)
    RETURN p, r, x
    """
    records = run_raw(query, {"person_id": person_id})

    if not records or records[0]["p"] is None:
        raise HTTPException(status_code=404, detail=f"Person '{person_id}' not found")

    acc = GraphAccumulator()
    for rec in records:
        acc.add_node(rec["p"])
        if rec["r"] is not None:
            acc.add_rel(rec["r"])
        if rec["x"] is not None:
            acc.add_node(rec["x"])

    return acc.to_json()


@app.get("/person/{person_id}/network")
def get_person_network(person_id: str, depth: int = Query(2, ge=1, le=4)):
    """
    Return the extended network up to `depth` hops away from this person
    (default 2, capped at 4 to avoid huge/slow queries). Same nodes/edges
    JSON shape — this is the main "investigate this person" endpoint.
    """
    # depth can't be parameterized inside a variable-length pattern in
    # Cypher, so it's injected directly — safe here since it's validated
    # as an int by FastAPI's Query(..., ge=1, le=4) above.
    query = f"""
    MATCH (p:Person {{person_id: $person_id}})
    OPTIONAL MATCH path = (p)-[*1..{depth}]-(x)
    RETURN p, path
    """
    records = run_raw(query, {"person_id": person_id})

    if not records or records[0]["p"] is None:
        raise HTTPException(status_code=404, detail=f"Person '{person_id}' not found")

    acc = GraphAccumulator()
    for rec in records:
        acc.add_node(rec["p"])
        if rec["path"] is not None:
            acc.add_path(rec["path"])

    return acc.to_json()


@app.get("/cluster/detect")
def detect_cluster():
    """
    Find the most densely connected group of persons in the graph using
    plain Cypher (no GDS plugin required): for each person, count how
    many other distinct persons they're linked to via a shared phone,
    account, vehicle, or case, then return the person with the highest
    such count plus everyone they're linked to that way.
    """
    query = """
    MATCH (p:Person)-[:OWNS|INVOLVED_IN]-(shared)-[:OWNS|INVOLVED_IN]-(other:Person)
    WHERE p.person_id <> other.person_id
    WITH p, other, collect(DISTINCT labels(shared)[0]) AS via_types, count(DISTINCT shared) AS shared_count
    WITH p, collect(DISTINCT other.person_id) AS connected_ids,
         count(DISTINCT other) AS connections,
         sum(shared_count) AS total_shared_links,
         collect(DISTINCT via_types) AS link_types_raw
    ORDER BY connections DESC
    LIMIT 1
    RETURN p.person_id AS center_person, p.name AS center_name,
           connected_ids, connections, total_shared_links, link_types_raw
    """
    records = run_query(query)

    if not records:
        raise HTTPException(status_code=404, detail="No cluster found — graph may be empty")

    row = records[0]
    cluster_ids = [row["center_person"]] + row["connected_ids"]

    # flatten the nested via_types lists into a readable set, e.g. "Phone, Case"
    flat_types = set()
    for group in row["link_types_raw"]:
        for t in group:
            flat_types.add(t)
    link_types_str = ", ".join(sorted(flat_types)) if flat_types else "shared entities"

    explanation = (
        f"{len(cluster_ids)} entities form a highly connected cluster around "
        f"{row['center_name']} ({row['center_person']}), linked via "
        f"{row['total_shared_links']} shared {link_types_str.lower()} connections. "
        f"Potentially significant network — requires investigator review."
    )

    return {
        "cluster_person_ids": cluster_ids,
        "center_person_id": row["center_person"],
        "center_person_name": row["center_name"],
        "connection_count": row["connections"],
        "shared_link_count": row["total_shared_links"],
        "explanation": explanation,
    }


@app.get("/search")
def search_person(name: str = Query(..., min_length=1)):
    """Simple partial, case-insensitive search for persons by name."""
    query = """
    MATCH (p:Person)
    WHERE toLower(p.name) CONTAINS toLower($name)
    RETURN p.person_id AS person_id, p.name AS name, p.city AS city
    ORDER BY p.name
    LIMIT 20
    """
    results = run_query(query, {"name": name})
    return {"count": len(results), "results": results}
