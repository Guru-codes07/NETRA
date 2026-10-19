# NETRA Prototype

**NETRA — Network Entity Tracking & Relationship Analysis**
**Status:** Personal project / portfolio prototype (originally started for SIH 2026, SIH26189)

## 1. Overview

NETRA is a working prototype for exploring relationships in synthetic criminal-investigation data. It loads CSV records into a Neo4j graph and exposes person/network queries through a FastAPI backend, with a React + Cytoscape frontend for interactive graph visualization, degree-based cluster detection, heuristic risk scoring, and a natural-language query assistant backed by a locally-run LLM.

The prototype addresses the problem of investigating fragmented records by connecting people with phones, bank accounts, vehicles, cases, calls, and transactions in one graph that can be queried from an investigator-oriented interface — in plain English as well as through direct lookups.

## 2. Architecture Diagram

```text
┌──────────────────────────────┐
│ Synthetic Investigation Data │
│            CSV               │
│ persons / phones / accounts  │
│ vehicles / cases / calls /   │
│ transactions                 │
└──────────────┬────────────────┘
               │
               │ Prototype/Graph/load_to_neo4j.py
               ▼
┌──────────────────────────────┐
│           Neo4j              │
│                               │
│ Person / Phone / Account     │
│ Vehicle / Case               │
│ + OWNS / CALLED /            │
│   TRANSACTED_WITH /          │
│   INVOLVED_IN                │
│ + risk_score / risk_level    │
│   (written by risk.py)       │
└──────────────┬────────────────┘
               │
               │ Bolt :7687
               ▼
┌──────────────────────────────┐        ┌───────────────────────┐
│       FastAPI Backend        │◄──────►│   Ollama (local LLM)  │
│       :8000                  │  HTTP  │   :11434               │
│                               │        │   Llama 3.1 8B         │
│ /person/{person_id}          │        └───────────────────────┘
│ /person/{person_id}/network  │
│ /cluster/detect              │
│ /search                      │
│ /ask            (llm.py)     │
│ /risk/precompute (risk.py)   │
│ /risk/{person_id}            │
└──────────────┬────────────────┘
               │ HTTP / JSON
               ▼
┌──────────────────────────────┐
│       React Frontend         │
│       Vite :5173             │
│                               │
│     Cytoscape.js Graph       │
│     (nodes colored by        │
│      risk_level)             │
│     Search / Cluster View    │
│     AI Assistant chat panel  │
└──────────────────────────────┘

Neo4j Browser: http://localhost:7474
```

The three backing services (Neo4j, Ollama, FastAPI backend) are orchestrated together with a single `docker-compose.yml` at the repository root. The frontend is run separately with `npm run dev` so it keeps Vite's hot-reload during development.

## 3. Tech Stack

| Layer | Technology | Version / Declaration | Actual use |
|---|---|---|---|
| Backend | Python | 3.11 (pinned via `Prototype/Backend/Dockerfile`, `python:3.11-slim`) | Backend and graph-loading scripts |
| Backend | FastAPI | `fastapi==0.115.0` (pinned in `requirements.txt`) | HTTP API |
| Backend | Uvicorn | `uvicorn[standard]==0.30.6` | ASGI server |
| Backend / Graph | Neo4j Python Driver | `neo4j==5.24.0` | Backend and loader connection to Neo4j |
| Backend | Requests | `requests==2.31.0` | HTTP calls from `llm.py` to the local Ollama API |
| Graph Database | Neo4j | `neo4j:5.24` (pinned in `docker-compose.yml`) | Stores nodes, relationships, and computed risk properties |
| AI | Ollama | `ollama/ollama:latest` (Docker image) | Serves the local LLM over an HTTP API |
| AI | Llama 3.1 8B | pulled via `ollama pull llama3.1:8b` | Generates Cypher from natural-language questions and explains results |
| Frontend | React | `^19.2.8` | UI |
| Frontend | React DOM | `^19.2.8` | React rendering |
| Frontend | Axios | `^1.20.0` | Backend HTTP requests |
| Frontend | Cytoscape | `^3.34.2` | Network graph visualization |
| Frontend | cytoscape-cose-bilkent | `^4.1.0` | Cytoscape graph layout |
| Frontend tooling | Vite | `^8.2.2` | Frontend development/build tooling |
| Frontend tooling | `@vitejs/plugin-react` | `^6.1.0` | React integration with Vite |
| Frontend tooling | oxlint | `^1.79.0` | JavaScript/React linting |
| Orchestration | Docker Compose | — | One-command local stack: Neo4j, data loader, Ollama, model pull, backend |

Relevant files:

- `Prototype/Backend/requirements.txt`
- `Prototype/Backend/Dockerfile`
- `Prototype/Loader/Dockerfile`
- `Prototype/Frontend/package.json`
- `Prototype/Frontend/vite.config.js`
- `docker-compose.yml`

## 4. Data Model

The graph is created by `Prototype/Graph/load_to_neo4j.py`.

### Node types

| Neo4j label | Source CSV | Key property / properties |
|---|---|---|
| `Person` | `persons.csv` | `person_id`, `name`, `age`, `gender`, `address`, `city`, plus `risk_score` and `risk_level` once `/risk/precompute` or `/risk/{person_id}` has been called |
| `Phone` | `phones.csv` | `phone_number` |
| `Account` | `bank_accounts.csv` | `account_id`, `bank_name` |
| `Vehicle` | `vehicles.csv` | `plate_number`, `vehicle_type` |
| `Case` | `cases.csv` | `case_id`, `description`, `location` |

`risk_score` (0–100, float) and `risk_level` (`"High"` / `"Medium"` / `"Low"`) are not part of the CSV data — they are computed and written onto `Person` nodes at runtime by `Prototype/Backend/risk.py` (see Section 6).

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

The following routes are defined in `Prototype/Backend/main.py`, backed by `llm.py` (AI Assistant) and `risk.py` (risk scoring).

### `GET /`

Health check.

```json
{"status": "NETRA API running"}
```

### `GET /person/{person_id}`

Returns the requested person's own node and their directly connected nodes/relationships.

```cypher
MATCH (p:Person {person_id: $person_id})
OPTIONAL MATCH (p)-[r]-(x)
RETURN p, r, x
```

**Path parameter:** `person_id: str`
**Success response:** graph JSON with `nodes` and `edges` generated by `GraphAccumulator`.
**Not found:** HTTP `404` with `Person '<person_id>' not found`.

### `GET /person/{person_id}/network`

Returns the extended network up to the requested number of hops.

**Path parameter:** `person_id: str`
**Query parameter:** `depth: int = Query(2, ge=1, le=4)`

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
**Success response fields:** `cluster_person_ids`, `center_person_id`, `center_person_name`, `connection_count`, `shared_link_count`, `explanation`.
**No result:** HTTP `404` with `No cluster found — graph may be empty`.

### `GET /search`

Performs a partial, case-insensitive search over `Person.name`.

**Query parameter:** `name: str = Query(..., min_length=1)`

Returns at most 20 results, ordered by name.

```json
{
  "count": 0,
  "results": [
    {"person_id": "...", "name": "...", "city": "..."}
  ]
}
```

### `POST /ask`

Natural-language question answering, backed by Llama 3.1 8B running locally via Ollama (`Prototype/Backend/llm.py`).

**Body:**

```json
{"question": "Which persons are involved in cases?"}
```

**Pipeline:** the question is sent to the LLM along with the graph schema, which generates a Cypher query; the query is validated as read-only (`CREATE`, `MERGE`, `DELETE`, `SET`, `REMOVE`, `DROP` are all rejected) before it is run against Neo4j; the result rows are sent back to the LLM, which produces a short plain-English explanation.

**Response:**

```json
{
  "question": "...",
  "cypher": "MATCH ... RETURN ...",
  "answer": "Plain-English explanation of the result.",
  "data": [{"...": "..."}],
  "error": null
}
```

Always returns HTTP `200`. Failure modes (Ollama unreachable, an unsafe generated query, a Cypher syntax error) are surfaced in the `error` field rather than as an HTTP error status, so the frontend can show a useful message instead of a blank failure.

### `POST /risk/precompute`

Recomputes a risk score for every `Person` in the graph and persists `risk_score` / `risk_level` onto each node (see Section 6 for the scoring method).

```json
{
  "scored_count": 80,
  "top_5_highest_risk": [
    {"person_id": "...", "name": "...", "risk_score": 92.4, "risk_level": "High", "degree": 11, "case_count": 3}
  ]
}
```

### `GET /risk/{person_id}`

On-demand risk score for a single person. Internally recomputes scores for the whole graph (cheap at this dataset size, so scores stay consistent with `/risk/precompute`) and returns just the requested person's entry.

**Not found:** HTTP `404` with `Person '<person_id>' not found`.

## 6. Key Features

### 6.1 Cluster Detection

`GET /cluster/detect` does **not** use Neo4j Graph Data Science (GDS), Louvain, Leiden, spectral clustering, or another full community-detection algorithm. It uses a plain Cypher query defined in `Prototype/Backend/main.py`.

The query looks for this two-step structure:

```text
Person A -- OWNS / INVOLVED_IN --> Shared Entity <-- OWNS / INVOLVED_IN -- Person B
```

```cypher
MATCH (p:Person)-[:OWNS|INVOLVED_IN]-(shared)-[:OWNS|INVOLVED_IN]-(other:Person)
WHERE p.person_id <> other.person_id
```

For each person, the query counts distinct `other` persons reachable through a shared entity (a `Phone`, `Account`, `Vehicle`, or `Case`), ordered by that count descending, and returns the single highest-degree person as the cluster center along with the connected person IDs.

The frontend displays this result as an **AI Insight**, but the detection itself is a deterministic Cypher query rather than a trained machine-learning model or Neo4j GDS community-detection algorithm.

### 6.2 AI Assistant (natural-language queries)

`POST /ask` lets an investigator type a question in plain English instead of writing Cypher by hand. It is implemented in `Prototype/Backend/llm.py` using a locally-run Llama 3.1 8B model served by Ollama — no external API calls, no data leaves the machine.

The flow is: generate Cypher from the question using the graph schema as context → validate the query is read-only → run it against Neo4j → explain the result rows back in plain English using a second call to the same model. The chat panel in the frontend (`ChatPanel.jsx`) shows the plain-English answer by default, with a "View query" toggle to inspect the exact Cypher that was run, for transparency.

This is a schema-aware query translator, not a general-purpose reasoning system — it works reliably for direct lookups and simple aggregations over the graph schema, and can fail or return empty results on questions that don't map cleanly onto the five node types and four relationship types in Section 4.

### 6.3 Risk Scoring

`POST /risk/precompute` and `GET /risk/{person_id}` score every `Person` from 0–100 using a hand-written heuristic in `Prototype/Backend/risk.py` — **this is not a trained machine-learning model**, and no classifier or prediction is involved. The formula:

```text
own_score     = 0.5 * (degree / max_degree) + 0.5 * (case_count / max_cases)
neighbor_avg  = average own_score of all persons directly linked via a shared
                phone, account, vehicle, or case
final_score   = (0.7 * own_score + 0.3 * neighbor_avg) * 100
```

`risk_level` is derived from `final_score`: `"High"` at ≥ 66, `"Medium"` at ≥ 33, `"Low"` below that. The neighbor term is a simple one-hop "guilt by association" factor — a person connected to otherwise-high-scoring people is nudged upward, even if their own degree/case count is modest.

Scores are written back onto `Person` nodes as plain properties, so once computed they flow through every other endpoint that returns `Person` nodes (`/person/{id}`, `/person/{id}/network`, `/cluster/detect`) without any additional backend code. The frontend colors `Person` nodes in the graph red/orange/green by `risk_level` as soon as the property is present (`GraphView.jsx`), and shows the numeric score in the "Selected Entity" sidebar panel when a node is clicked.

This is a structural heuristic over synthetic data intended to prioritize which connections an investigator looks at first — it is **not** a criminality or guilt prediction (see Section 9).

## 7. Setup Instructions

The repository currently contains the synthetic CSV data directly. There is no data-generation script, so there is no command for generating a new dataset — the checked-in CSV files are the dataset used by the prototype.

### Prerequisites

Install:

- Docker and Docker Compose
- Node.js and npm (for the frontend)

A native Python/Neo4j install is only needed if you choose **not** to use Docker (see the manual path below).

### Option A — One-command backend stack (recommended)

From the repository root:

```bash
docker-compose up --build
```

This single command: starts Neo4j and waits until it's healthy; builds and runs a one-shot loader container (`Prototype/Loader/Dockerfile`) that loads the CSVs into Neo4j; starts Ollama and waits until it's healthy; pulls `llama3.1:8b` into it; then builds and starts the FastAPI backend on port 8000, wired to both.

The first run is slow — pulling the Neo4j and Ollama images plus the ~4.7GB Llama model. Subsequent runs are fast, since Docker caches all of it in named volumes (`neo4j_data`, `ollama_data`).

Then, in a separate terminal, start the frontend (kept outside Docker Compose so Vite's hot-reload still works during development):

```bash
cd Prototype/Frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

### Option B — Running each service manually

If you'd rather not use Docker Compose:

```bash
# Terminal 1 — Neo4j
docker run --name netra-neo4j \
  -p 7474:7474 \
  -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password123 \
  neo4j:5.24

# Terminal 2 — Load synthetic CSV data
cd Prototype/Data
python ../Graph/load_to_neo4j.py

# Terminal 3 — Ollama (skip if already running as a background service)
ollama serve
ollama pull llama3.1:8b

# Terminal 4 — Backend
cd Prototype/Backend
python -m pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Terminal 5 — Frontend
cd Prototype/Frontend
npm install
npm run dev
```

`db.py` and `llm.py` both read their connection settings (`NEO4J_URI`, `OLLAMA_HOST`, etc.) from environment variables when set, falling back to `localhost` defaults — so this manual path and the Docker Compose path both work from the same codebase without edits.

The backend CORS configuration explicitly permits `http://localhost:3000` and `http://localhost:5173`.

## 8. Current Limitations / Honest Status

The current repository is a **working graph-analysis prototype with heuristic risk scoring and a local-LLM query assistant** — not a complete production criminal-intelligence platform.

Currently implemented:

- Synthetic CSV-based investigation data, loaded via Docker or manually
- Neo4j graph with Person, Phone, Account, Vehicle, and Case nodes
- `OWNS`, `CALLED`, `TRANSACTED_WITH`, and `INVOLVED_IN` relationships
- Direct person lookup and configurable network traversal (depth 1–4)
- Case-insensitive person-name search
- Degree-based cluster detection using plain Cypher
- Natural-language question answering via a locally-run Llama 3.1 8B model, with read-only query validation
- Heuristic risk scoring (0–100) written back onto Person nodes, with an on-demand per-person endpoint
- React frontend with Cytoscape graph visualization, node selection, cluster highlighting, risk-based node coloring, and a chat panel for the AI Assistant
- One-command local stack via Docker Compose (Neo4j, data loader, Ollama, model pull, backend)
- Pinned dependency versions (`requirements.txt`, Docker image tags)

Not currently implemented:

- Neo4j GDS community detection such as Louvain or Leiden
- Trained machine-learning models for risk, classification, or entity resolution (the risk score is a hand-written structural heuristic, not a model)
- Named-entity recognition or general NLP beyond schema-aware Cypher generation
- ML-based anomaly detection
- Predictive policing or criminality prediction
- Real government, CDR, banking, police, or intelligence-system integration
- Authentication or role-based access control (RBAC)
- Encryption/audit infrastructure beyond the local prototype setup
- Production deployment / cloud hosting (currently local-only via Docker Compose or manual setup)
- Real-world personal or criminal datasets
- Automated determination of criminal guilt

## 9. Responsible AI Note

NETRA is designed as an investigative decision-support prototype. It flags potentially significant relationships, network structures, and risk scores for **investigator review**; it does not identify, classify, or label individuals as criminals and does not determine guilt. The cluster-detection and risk-scoring features are deterministic graph queries and a hand-written heuristic formula over synthetic data — neither is a trained predictive model. The AI Assistant translates questions into read-only Cypher queries and summarizes results; it does not draw conclusions about guilt or make accusations, and its explanations are scoped to describing connections and patterns present in the data. Final investigative decisions remain human-led and subject to applicable law, authorization, privacy requirements, and data-governance controls.
