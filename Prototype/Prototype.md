# NETRA Prototype

**Smart India Hackathon 2026 — SIH26189**  
**Theme:** Blockchain & Cybersecurity  
**Team:** NETRA — Network Entity Tracking Relationship Analysis

## 1. Overview

NETRA is a working prototype for exploring relationships in synthetic criminal-investigation data. It loads CSV records into a Neo4j graph and exposes person/network queries through a FastAPI backend, with a React + Cytoscape frontend for interactive graph visualization and basic cluster detection.

The prototype addresses the problem of investigating fragmented records by connecting people with phones, bank accounts, vehicles, cases, calls, and transactions in one graph that can be queried from an investigator-oriented interface.

## 2. Architecture Diagram

```text
┌──────────────────────────────┐
│ Synthetic Investigation Data │
│            CSV               │
│ persons / phones / accounts  │
│ vehicles / cases / calls /   │
│ transactions                │
└──────────────┬───────────────┘
               │
               │ Prototype/Graph/load_to_neo4j.py
               ▼
┌──────────────────────────────┐
│           Neo4j              │
│                              │
│ Person / Phone / Account     │
│ Vehicle / Case               │
│ + OWNS / CALLED /            │
│   TRANSACTED_WITH /          │
│   INVOLVED_IN                │
└──────────────┬───────────────┘
               │
               │ Bolt :7687
               ▼
┌──────────────────────────────┐
│       FastAPI Backend        │
│       :8000                  │
│                              │
│ /person/{person_id}          │
│ /person/{person_id}/network  │
│ /cluster/detect              │
│ /search                      │
└──────────────┬───────────────┘
               │ HTTP / JSON
               ▼
┌──────────────────────────────┐
│       React Frontend         │
│       Vite :5173             │
│                              │
│     Cytoscape.js Graph       │
│     Search / Cluster View    │
└──────────────────────────────┘

Neo4j Browser: http://localhost:7474
```

## 3. Tech Stack

Only technologies present in the prototype source/configuration are listed below. Backend `requirements.txt` does not pin package versions.

| Layer | Technology | Version / Declaration | Actual use |
|---|---|---|---|
| Backend | Python | — | Backend and graph-loading scripts |
| Backend | FastAPI | unpinned in `Prototype/Backend/requirements.txt` | HTTP API |
| Backend | Uvicorn | `uvicorn[standard]`, unpinned | ASGI server |
| Backend / Graph | Neo4j Python Driver | `neo4j`, unpinned | Backend and loader connection to Neo4j |
| Graph Database | Neo4j | Docker image/version not specified in repository | Stores nodes and relationships |
| Frontend | React | `^19.2.8` | UI |
| Frontend | React DOM | `^19.2.8` | React rendering |
| Frontend | Axios | `^1.20.0` | Backend HTTP requests |
| Frontend | Cytoscape | `^3.34.2` | Network graph visualization |
| Frontend | cytoscape-cose-bilkent | `^4.1.0` | Cytoscape graph layout |
| Frontend tooling | Vite | `^8.2.2` | Frontend development/build tooling |
| Frontend tooling | `@vitejs/plugin-react` | `^6.1.0` | React integration with Vite |
| Frontend tooling | oxlint | `^1.79.0` | JavaScript/React linting |

Relevant files:

- `Prototype/Backend/requirements.txt`
- `Prototype/Frontend/package.json`
- `Prototype/Frontend/vite.config.js`

## 4. Data Model

The graph is created by `Prototype/Graph/load_to_neo4j.py`.

### Node types

| Neo4j label | Source CSV | Key property / properties |
|---|---|---|
| `Person` | `persons.csv` | `person_id`, `name`, `age`, `gender`, `address`, `city` |
| `Phone` | `phones.csv` | `phone_number` |
| `Account` | `bank_accounts.csv` | `account_id`, `bank_name` |
| `Vehicle` | `vehicles.csv` | `plate_number`, `vehicle_type` |
| `Case` | `cases.csv` | `case_id`, `description`, `location` |

### Relationship types

| Relationship | Direction created by loader | Meaning in the prototype |
|---|---|---|
| `OWNS` | `Person -> Phone`, `Person -> Account`, `Person -> Vehicle` | Links a person to an owned phone, bank account, or vehicle |
| `CALLED` | `Phone -> Phone` | Links caller and receiver phone numbers; stores `timestamp` and `duration_seconds` |
| `TRANSACTED_WITH` | `Account -> Account` | Links source and destination accounts; stores `timestamp` and `amount` |
| `INVOLVED_IN` | `Person -> Case` | Links a person to a case |

The case loader reads `linked_person_ids` from `cases.csv` as a comma-separated list and creates one `INVOLVED_IN` relationship for each listed person.

### CSV schemas in the current prototype

| File | Columns |
|---|---|
| `persons.csv` | `person_id,name,age,gender,address,city` |
| `phones.csv` | `phone_number,owner_id` |
| `bank_accounts.csv` | `account_id,owner_id,bank_name` |
| `vehicles.csv` | `plate_number,owner_id,vehicle_type` |
| `cases.csv` | `case_id,description,linked_person_ids,location` |
| `call_records.csv` | `caller_number,receiver_number,timestamp,duration_seconds` |
| `transactions.csv` | `from_account,to_account,amount,timestamp` |

The checked-in dataset currently contains 80 persons, 110 phone records, 80 bank-account records, 33 vehicle records, 16 case records, 325 call records, and 156 transaction records.

## 5. API Endpoints

The following routes are defined directly in `Prototype/Backend/main.py`.

### `GET /`

Health check.

**Response:**

```json
{"status": "NETRA API running"}
```

### `GET /person/{person_id}`

Returns the requested person's own node and their directly connected nodes/relationships. The Cypher query is:

```cypher
MATCH (p:Person {person_id: $person_id})
OPTIONAL MATCH (p)-[r]-(x)
RETURN p, r, x
```

**Path parameter:**

- `person_id: str`

**Success response:** graph JSON with `nodes` and `edges` generated by `GraphAccumulator`.

**Not found:** HTTP `404` with `Person '<person_id>' not found`.

### `GET /person/{person_id}/network`

Returns the extended network up to the requested number of hops.

**Path parameter:**

- `person_id: str`

**Query parameter:**

- `depth: int = Query(2, ge=1, le=4)`

The default depth is 2 and FastAPI restricts it to 1–4. The query uses a variable-length Cypher pattern:

```cypher
MATCH (p:Person {person_id: $person_id})
OPTIONAL MATCH path = (p)-[*1..{depth}]-(x)
RETURN p, path
```

**Success response:** graph JSON with `nodes` and `edges`.

**Not found:** HTTP `404` with `Person '<person_id>' not found`.

### `GET /cluster/detect`

Runs the prototype's degree-based cluster detection query and returns the person with the highest number of distinct connected people through shared graph entities, along with those connected person IDs.

**Parameters:** none.

**Success response fields:**

- `cluster_person_ids`
- `center_person_id`
- `center_person_name`
- `connection_count`
- `shared_link_count`
- `explanation`

**No result:** HTTP `404` with `No cluster found — graph may be empty`.

### `GET /search`

Performs a partial, case-insensitive search over `Person.name`.

**Query parameter:**

- `name: str = Query(..., min_length=1)`

The backend returns at most 20 results, ordered by name.

**Response shape:**

```json
{
  "count": 0,
  "results": [
    {
      "person_id": "...",
      "name": "...",
      "city": "..."
    }
  ]
}
```

## 6. Key Feature: Cluster Detection

`GET /cluster/detect` does **not** use Neo4j Graph Data Science (GDS), Louvain, Leiden, spectral clustering, or another full community-detection algorithm. It uses a plain Cypher query defined in `Prototype/Backend/main.py`.

The query looks for this two-step structure:

```text
Person A -- OWNS / INVOLVED_IN --> Shared Entity <-- OWNS / INVOLVED_IN -- Person B
```

In Cypher, the relevant pattern is:

```cypher
MATCH (p:Person)-[:OWNS|INVOLVED_IN]-(shared)-[:OWNS|INVOLVED_IN]-(other:Person)
WHERE p.person_id <> other.person_id
```

For each person, the query counts distinct `other` persons reachable through a shared entity. The shared entity can be a `Phone`, `Account`, `Vehicle`, or `Case`, because those are the non-Person nodes connected through `OWNS` or `INVOLVED_IN`.

The result is ordered by the number of distinct connected people:

```cypher
ORDER BY connections DESC
LIMIT 1
```

So the prototype selects **one center person with the highest degree-like count of people connected through shared entities**. It then returns the center person plus those connected person IDs and reports the number of shared links and the entity types involved.

The frontend displays this result as an **AI Insight**, but the current implementation of the detection itself is a deterministic Cypher query rather than a trained machine-learning model or Neo4j GDS community-detection algorithm.

## 7. Setup Instructions

The repository currently contains the synthetic CSV data directly. **There is no data-generation script in `Prototype/`**, so there is no implemented command for generating a new dataset. The checked-in CSV files are the dataset used by the prototype.

### Prerequisites

Install:

- Python
- Node.js and npm
- Docker

### Step 1 — Start Neo4j

The repository does not contain a Docker Compose file or other Neo4j container configuration. The application code expects:

- Bolt: `bolt://localhost:7687`
- User: `neo4j`
- Password: `password123`
- Neo4j Browser: port `7474`

To run a Neo4j container matching those settings:

```bash
docker run --name netra-neo4j \
  -p 7474:7474 \
  -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password123 \
  neo4j:latest
```

The `neo4j:latest` image tag is **not specified by the repository**; it is used here because the repository does not pin a Neo4j Docker image version.

Neo4j Browser will be available at `http://localhost:7474` and the Bolt connection used by the code is `bolt://localhost:7687`.

### Step 2 — Load the CSV data into Neo4j

`Prototype/Graph/load_to_neo4j.py` sets `DATA_DIR = "."`, so it must be run from the directory containing the CSV files.

From the repository root:

```bash
cd Prototype/Data
python ../Graph/load_to_neo4j.py
```

The loader reads:

```text
persons.csv
phones.csv
bank_accounts.csv
vehicles.csv
call_records.csv
transactions.csv
cases.csv
```

It clears the existing Neo4j database first with:

```cypher
MATCH (n) DETACH DELETE n
```

and then loads nodes and relationships in batches of 500 rows.

The Neo4j connection settings are defined in `Prototype/Graph/load_to_neo4j.py`:

```text
URI:      bolt://localhost:7687
Username: neo4j
Password: password123
```

### Step 3 — Start the FastAPI backend

Install the backend dependencies:

```bash
cd Prototype/Backend
python -m pip install -r requirements.txt
```

Start the API on port 8000:

```bash
uvicorn main:app --reload --port 8000
```

The frontend's `Prototype/Frontend/src/api.js` is configured to call:

```text
http://localhost:8000
```

### Step 4 — Start the React frontend

In a new terminal:

```bash
cd Prototype/Frontend
npm install
npm run dev
```

The repository's Vite configuration does not explicitly set a port, so Vite uses its normal development-server default of `5173`.

Open:

```text
http://localhost:5173
```

The backend CORS configuration explicitly permits:

```text
http://localhost:3000
http://localhost:5173
```

### Complete local startup sequence

```bash
# Terminal 1 — Neo4j
docker run --name netra-neo4j \
  -p 7474:7474 \
  -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password123 \
  neo4j:latest

# Terminal 2 — Load synthetic CSV data
cd Prototype/Data
python ../Graph/load_to_neo4j.py

# Terminal 3 — Backend
cd Prototype/Backend
python -m pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Terminal 4 — Frontend
cd Prototype/Frontend
npm install
npm run dev
```

## 8. Current Limitations / Honest Status

The current repository is a **working graph-analysis prototype**, not a complete production criminal-intelligence platform.

Currently implemented:

- Synthetic CSV-based investigation data
- Neo4j graph loading
- Person, Phone, Account, Vehicle, and Case nodes
- `OWNS`, `CALLED`, `TRANSACTED_WITH`, and `INVOLVED_IN` relationships
- Direct person lookup
- Configurable person-network traversal with depth 1–4
- Case-insensitive person-name search
- Basic degree-based cluster detection using plain Cypher
- React frontend with Cytoscape graph visualization
- Node selection in the graph
- Highlighting of people returned by cluster detection

Not currently implemented:

- Neo4j GDS community detection such as Louvain or Leiden
- Machine-learning-based criminal-network classification
- NLP or named-entity recognition
- Entity-resolution models
- ML-based anomaly detection
- Predictive policing or criminality prediction
- Real government data integration
- Real CDR, banking, police, or intelligence-system integration
- Authentication
- Role-based access control (RBAC)
- Encryption/audit infrastructure beyond the local prototype setup
- Production deployment architecture
- Real-world personal or criminal datasets
- Automated determination of criminal guilt

The backend dependencies are also unpinned in `Prototype/Backend/requirements.txt`, and the Neo4j Docker image version is not pinned in the repository. These should be addressed before treating the prototype as a reproducible production deployment.

## 9. Responsible AI Note

NETRA is designed as an investigative decision-support prototype. It flags potentially significant relationships and network structures for **investigator review**; it does not identify, classify, or label individuals as criminals and does not determine guilt. The current cluster feature is a graph query over synthetic data, and any future AI/ML components should provide appropriate evidence, uncertainty, and human oversight. Final investigative decisions remain human-led and subject to applicable law, authorization, privacy requirements, and data-governance controls.
