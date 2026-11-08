# NETRA Prototype

**NETRA — Network Entity Tracking & Relationship Analysis**
**Status:** Personal project / portfolio prototype (originally started for SIH 2026, SIH26189)

## 1. Overview

NETRA is a working prototype for exploring relationships in synthetic criminal-investigation data. It loads CSV records into a Neo4j graph and exposes person/network queries through a FastAPI backend, with a React + Cytoscape frontend for interactive graph visualization, degree-based cluster detection, heuristic risk scoring, a natural-language query assistant backed by a locally-run LLM, and a full investigator workflow layered on top — a case browser, a summary dashboard, a watchlist, and free-text notes on any entity.

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
│ Vehicle / Case / Note        │
│ + OWNS / CALLED /            │
│   TRANSACTED_WITH /          │
│   INVOLVED_IN / ANNOTATES    │
│ + risk_score / risk_level /  │
│   on_watchlist (written by   │
│   risk.py / watchlist.py)    │
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
│ /person/{person_id}/timeline │
│ /cluster/detect              │
│ /search                      │
│ /ask            (llm.py)     │
│ /risk/...        (risk.py)   │
│ /cases/...        (cases.py) │
│ /dashboard      (dashboard.py)│
│ /watchlist/...  (watchlist.py)│
│ /entities/.../notes (notes.py)│
└──────────────┬────────────────┘
               │ HTTP / JSON
               ▼
┌──────────────────────────────┐
│       React Frontend         │
│       Vite :5173             │
│                               │
│  View switcher: Graph /      │
│  Cases / Dashboard           │
│                               │
│     Cytoscape.js Graph       │
│     (nodes colored by        │
│      risk_level, ringed      │
│      gold if on_watchlist)   │
│     Search / Cluster View    │
│     AI Assistant chat panel  │
│     Watchlist / Notes /      │
│     Timeline side panels     │
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
| Graph Database | Neo4j | `neo4j:5.24` (pinned in `docker-compose.yml`) | Stores nodes, relationships, and computed/flagged properties |
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

The graph is created by `Prototype/Graph/load_to_neo4j.py`. `Note` nodes, `risk_score`/`risk_level`, and `on_watchlist` are added at runtime by the backend, not by the loader.

### Node types

| Neo4j label | Source | Key property / properties |
|---|---|---|
| `Person` | `persons.csv` | `person_id`, `name`, `age`, `gender`, `address`, `city`, plus `risk_score`, `risk_level` (written by `risk.py`), and `on_watchlist` (written by `watchlist.py`) once those endpoints have been called |
| `Phone` | `phones.csv` | `phone_number` |
| `Account` | `bank_accounts.csv` | `account_id`, `bank_name` |
| `Vehicle` | `vehicles.csv` | `plate_number`, `vehicle_type` |
| `Case` | `cases.csv` | `case_id`, `description`, `location` |
| `Note` | Runtime, via `notes.py` | `note_id`, `text`, `created_at` — one node per note, not per entity, so an entity can carry many |

### Relationship types

| Relationship | Direction | Meaning |
|---|---|---|
| `OWNS` | `Person -> Phone`, `Person -> Account`, `Person -> Vehicle` | Created by the loader. Links a person to an owned phone, bank account, or vehicle |
| `CALLED` | `Phone -> Phone` | Created by the loader. Stores `timestamp` and `duration_seconds` |
| `TRANSACTED_WITH` | `Account -> Account` | Created by the loader. Stores `timestamp` and `amount` |
| `INVOLVED_IN` | `Person -> Case` | Created by the loader, from `cases.csv`'s `linked_person_ids` column |
| `ANNOTATES` | `Note -> (any entity)` | Created at runtime by `notes.py` when a note is added. The target can be a Person, Phone, Account, Vehicle, or Case |

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

22 routes total, defined in `Prototype/Backend/main.py` and backed by the modules named below.

### Core graph

**`GET /`** — health check. Returns `{"status": "NETRA API running"}`.

**`GET /person/{person_id}`** — the person's own node plus directly connected nodes/relationships. `404` if not found.

**`GET /person/{person_id}/network`** — extended network up to `depth` hops (`Query(2, ge=1, le=4)`). `404` if not found.

**`GET /cluster/detect`** — the prototype's degree-based cluster detection (see Section 6.1). `404` if the graph is empty.

**`GET /search`** — case-insensitive partial search over `Person.name` (`Query(..., min_length=1)`), max 20 results.

### AI Assistant (`llm.py`)

**`POST /ask`** — body `{"question": "..."}`. Generates Cypher from the question via Llama 3.1, validates it's read-only, runs it, and asks the model to explain the result. Always returns `200`; failures surface in the `error` field. See Section 6.2.

### Risk scoring (`risk.py`)

**`POST /risk/precompute`** — recomputes and persists `risk_score`/`risk_level` on every Person. Returns `scored_count` and `top_5_highest_risk`.

**`GET /risk/{person_id}`** — on-demand score for one person (recomputes the whole graph internally for consistency). `404` if not found.

### Timeline (`timeline.py`)

**`GET /person/{person_id}/timeline`** — merged, chronologically-sorted list of that person's calls (via owned phones) and transactions (via owned accounts). `404` if not found.

### Cases (`cases.py`)

**`GET /cases`** — every case, with `linked_person_count` for each.

**`GET /cases/{case_id}`** — full detail: the case's own fields, every linked person (highest risk first, if scored), and the phones/accounts/vehicles those persons own (the dataset's closest proxy for case evidence — see Section 6.4). `404` if not found.

### Dashboard (`dashboard.py`)

**`GET /dashboard`** — landing-page summary:

```json
{
  "counts": {"persons": 80, "phones": 110, "accounts": 80, "vehicles": 33, "cases": 16, "calls": 325, "transactions": 156},
  "risk_distribution": {"High": 0, "Medium": 0, "Low": 0},
  "scored_person_count": 0,
  "most_connected": [{"person_id": "...", "name": "...", "degree": 11}],
  "busiest_cases": [{"case_id": "...", "description": "...", "linked_person_count": 7}]
}
```

`risk_distribution` is all zeros until `/risk/precompute` has been run at least once.

### Watchlist (`watchlist.py`)

**`GET /watchlist`** — every person currently flagged, alphabetical by name.

**`POST /watchlist/{person_id}`** — sets `on_watchlist = true` on that Person node. `404` if not found.

**`DELETE /watchlist/{person_id}`** — sets `on_watchlist = false`. `404` if not found.

Because the flag lives directly on the Person node, every other endpoint that returns Person nodes (`/person/{id}`, `/network`, `/cluster/detect`, `/cases/{id}`, `/search` results once loaded into a graph view) carries it automatically — no per-endpoint wiring needed on the backend, and the frontend highlights it the same way everywhere (gold ring in `GraphView.jsx`).

### Notes (`notes.py`)

**`GET /entities/{entity_type}/{entity_id}/notes`** — every note on that entity, newest first. `entity_type` must be one of `Person`, `Phone`, `Account`, `Vehicle`, `Case`; `400` otherwise.

**`POST /entities/{entity_type}/{entity_id}/notes`** — body `{"text": "..."}` (1–2000 chars). Creates a new `Note` node linked via `ANNOTATES`. `404` if the target entity doesn't exist, `400` for an invalid `entity_type`.

**`DELETE /notes/{note_id}`** — deletes a single note. `404` if not found.

## 6. Key Features

### 6.1 Cluster Detection

`GET /cluster/detect` does **not** use Neo4j Graph Data Science (GDS), Louvain, Leiden, or another full community-detection algorithm — it's a plain Cypher query in `main.py` that counts, for each person, how many other distinct persons are reachable through a shared `Phone`, `Account`, `Vehicle`, or `Case`, and returns the single highest-degree person as the cluster center. The frontend presents this as an "AI Insight," but the detection itself is deterministic, not learned.

### 6.2 AI Assistant (natural-language queries)

`POST /ask`, implemented in `llm.py`, uses a locally-run Llama 3.1 8B model served by Ollama — no external API calls, no data leaves the machine. Flow: generate Cypher from the question (using the graph schema as context) → validate it's read-only (`CREATE`, `MERGE`, `DELETE`, `SET`, `REMOVE`, `DROP` are all rejected) → run it against Neo4j → ask the model to explain the result rows in plain English. The chat panel (`ChatPanel.jsx`) shows the explanation by default, with a "View query" toggle for the exact Cypher, for transparency.

This is a schema-aware query translator, not a general-purpose reasoning system — it works reliably for direct lookups and simple aggregations over the five node types and five relationship types in Section 4, and can fail or return empty results outside that.

### 6.3 Risk Scoring

`risk.py` scores every Person 0–100 with a hand-written heuristic — **not a trained machine-learning model**:

```text
own_score     = 0.5 * (degree / max_degree) + 0.5 * (case_count / max_cases)
neighbor_avg  = average own_score of all persons directly linked via a shared
                phone, account, vehicle, or case
final_score   = (0.7 * own_score + 0.3 * neighbor_avg) * 100
```

`risk_level` is `"High"` at ≥ 66, `"Medium"` at ≥ 33, `"Low"` below that. The neighbor term is a one-hop "guilt by association" nudge. Scores are written back onto Person nodes as plain properties, so they flow through every other endpoint automatically; the frontend colors Person nodes red/orange/green by `risk_level` as soon as it's present.

### 6.4 Case View

`cases.py` backs a dedicated case-browsing page (`CasesPage.jsx`). `GET /cases` lists every case with how many people are linked to it; `GET /cases/{case_id}` drills into one case, returning its linked persons (sorted by risk, if scored) and the phones/accounts/vehicles those persons own.

**Honesty note:** the dataset has no dedicated "evidence" entity — only Person, Phone, Account, Vehicle, and Case. The "linked entities" section of the case detail (each linked person's owned phones/accounts/vehicles) is used as the closest available proxy for evidence, and is labeled as such in both this document and the UI itself, rather than inventing an evidence model the data doesn't support.

### 6.5 Dashboard

`dashboard.py` backs a landing page (`DashboardPage.jsx`) shown before diving into the graph: total entity counts, a risk-level distribution bar chart (High/Medium/Low — all zero until risk scores have been computed at least once), the 5 most-connected people by degree, and the 5 busiest cases by linked-person count. Clicking a person or case from this page jumps into the Graph or Case view respectively.

**Known gap:** jumping from a busiest-case entry currently switches to Case View but does not yet auto-select that specific case — the person lands on the case list and selects it manually. Auto-selecting it is a small follow-up (passing an initial case id into `CasesPage.jsx`), not yet implemented.

### 6.6 Watchlist

`watchlist.py` lets an investigator flag specific people so they stay visually highlighted in **every** graph view, regardless of how that view was reached — search, network traversal, cluster detection, or case view. This works by writing a single `on_watchlist` boolean property directly onto the Person node (the same pattern as risk scoring), rather than tracking watchlist state separately in the frontend. Because it's a property on the node itself, it's returned by every endpoint that already returns Person nodes, with no additional backend wiring per endpoint.

In the UI, a watchlisted Person node gets a gold double-border ring in `GraphView.jsx` (Cytoscape selector `node[?onWatchlist]`, which checks truthiness rather than mere attribute existence), and the sidebar's `WatchlistPanel.jsx` lists everyone currently flagged, refreshed after each toggle.

### 6.7 Notes

`notes.py` lets an investigator attach free-text, timestamped notes to any entity in the graph — Person, Phone, Account, Vehicle, or Case. Each note is its own `(:Note {note_id, text, created_at})` node, linked to its target via an `ANNOTATES` relationship, rather than a property on the target node — this allows multiple notes per entity, each with its own timestamp, and clean single-note deletion without touching the entity it's attached to. `entity_type` is validated against a fixed whitelist of the five known labels before being interpolated into a Cypher label (labels can't be parameterized directly in Cypher), so there is no injection risk. The frontend's `NotesPanel.jsx` shows notes for whichever entity is currently selected, with inline add/delete.

## 7. Setup Instructions

The repository currently contains the synthetic CSV data directly. There is no data-generation script — the checked-in CSV files are the dataset used by the prototype.

### Prerequisites

- Docker and Docker Compose
- Node.js and npm (for the frontend)

### Option A — One-command backend stack (recommended)

From the repository root:

```bash
docker-compose up --build
```

This starts Neo4j (waits until healthy) → builds and runs a one-shot loader container (`Prototype/Loader/Dockerfile`) that loads the CSVs → starts Ollama (waits until healthy) → pulls `llama3.1:8b` → builds and starts the FastAPI backend on port 8000, wired to both.

First run is slow (pulling images + the ~4.7GB model); subsequent runs are fast via the `neo4j_data`/`ollama_data` named volumes.

Then, separately (kept outside Compose so Vite's hot-reload still works):

```bash
cd Prototype/Frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

### Option B — Running each service manually

```bash
# Terminal 1 — Neo4j
docker run --name netra-neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password123 neo4j:5.24

# Terminal 2 — Load synthetic CSV data
cd Prototype/Data
python ../Graph/load_to_neo4j.py

# Terminal 3 — Ollama
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

`db.py` and `llm.py` read their connection settings from environment variables when set, falling back to `localhost` defaults, so both setup paths work from the same codebase without edits. The backend's CORS configuration permits `http://localhost:3000` and `http://localhost:5173`.

## 8. Current Limitations / Honest Status

Currently implemented:

- Synthetic CSV-based investigation data, loaded via Docker or manually
- Neo4j graph with Person, Phone, Account, Vehicle, Case, and runtime-created Note nodes
- `OWNS`, `CALLED`, `TRANSACTED_WITH`, `INVOLVED_IN`, and `ANNOTATES` relationships
- Direct person lookup, configurable network traversal (depth 1–4), case-insensitive name search
- Degree-based cluster detection using plain Cypher
- Natural-language question answering via a locally-run Llama 3.1 8B model, with read-only query validation
- Heuristic risk scoring (0–100), pre-computed for all persons or on-demand for one
- Per-person call/transaction timeline
- Case browser with linked persons and linked entities (phones/accounts/vehicles as an evidence proxy)
- Landing-page dashboard: counts, risk distribution, most-connected people, busiest cases
- Watchlist: flag/unflag persons, persisted on the node, highlighted consistently across every view
- Free-text, timestamped notes on any entity type
- CSV export and printable-PDF export of the current graph view
- React frontend with Cytoscape visualization, a Graph/Cases/Dashboard view switcher, risk- and watchlist-based node styling, and panels for AI chat, timeline, watchlist, and notes
- One-command local stack via Docker Compose
- Pinned dependency versions (`requirements.txt`, Docker image tags)

Not currently implemented:

- Neo4j GDS community detection such as Louvain or Leiden
- Trained machine-learning models for risk, classification, or entity resolution (risk scoring is a hand-written heuristic, not a model)
- Named-entity recognition or general NLP beyond schema-aware Cypher generation
- ML-based anomaly detection, predictive policing, or criminality prediction
- A dedicated evidence data model — the Case view's "linked entities" are a proxy, not real evidence records
- Auto-selecting a specific case when jumping from the Dashboard's busiest-cases list
- Real government, CDR, banking, police, or intelligence-system integration
- Authentication or role-based access control (RBAC)
- Automated test suite or CI/CD pipeline
- Encryption/audit infrastructure beyond the local prototype setup
- Production deployment / cloud hosting (currently local-only via Docker Compose or manual setup)
- Real-world personal or criminal datasets
- Automated determination of criminal guilt

## 9. Responsible AI Note

NETRA is designed as an investigative decision-support prototype. It flags potentially significant relationships, network structures, and risk scores for **investigator review**; it does not identify, classify, or label individuals as criminals and does not determine guilt. Cluster detection and risk scoring are deterministic graph queries and a hand-written heuristic formula over synthetic data — neither is a trained predictive model. The watchlist and notes features are investigator-driven annotations, not automated flags, and carry no inference of guilt on their own. The AI Assistant translates questions into read-only Cypher queries and summarizes results; it does not draw conclusions about guilt or make accusations. Final investigative decisions remain human-led and subject to applicable law, authorization, privacy requirements, and data-governance controls.
