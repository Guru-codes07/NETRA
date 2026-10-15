 NETRA — Network Entity Tracking & Relationship Analysis

> **Smart India Hackathon (SIH) 2026** · Problem Statement: **SIH26189**  
> **Project:** AI-Powered Criminal Network Analysis System

NETRA is a prototype investigation-support platform that turns connected records into an interactive graph. It helps authorized investigators explore relationships between people, phone numbers, bank accounts, vehicles, and cases, identify highly connected groups, and ask natural-language questions about the graph.

**Core workflow:** Synthetic CSV data → Neo4j graph → FastAPI API → React/Cytoscape interface → optional natural-language queries through Ollama.

> **Important:** NETRA is a research/prototype tool, not a system for determining guilt. Its current dataset is synthetic. Graph connections and cluster results are leads for human review, not proof of wrongdoing.

---

## Contents

- [Current capabilities](#current-capabilities)
- [Architecture](#architecture)
- [Technology stack](#technology-stack)
- [Repository structure](#repository-structure)
- [Graph data model](#graph-data-model)
- [Requirements](#requirements)
- [Run locally](#run-locally)
- [Run with Docker Compose](#run-with-docker-compose)
- [API reference](#api-reference)
- [Frontend workflow](#frontend-workflow)
- [Configuration](#configuration)
- [Limitations and safety notes](#limitations-and-safety-notes)
- [Roadmap](#roadmap)
- [Team and project](#team-and-project)

---

## Current capabilities

- **Interactive relationship graph:** Visualizes entities and their relationships using React and Cytoscape.js.
- **Person search:** Search for people by a partial, case-insensitive name match.
- **Person network exploration:** Load a person’s connected network, with a configurable hop depth supported by the API.
- **Cluster detection:** Finds a highly connected group using shared entities such as phones, accounts, vehicles, and cases. The result is a heuristic for investigation, not a formal criminal-network classification.
- **Natural-language graph questions:** Ask questions in plain English. A local Llama 3.1 model served by Ollama generates a read-only Cypher query, which is executed against Neo4j; the interface can show the generated query for transparency.
- **Explainable response payloads:** The AI query endpoint returns the question, generated Cypher, result rows, a plain-English answer, and an error field when applicable.
- **Synthetic investigation data:** CSV files provide reproducible sample records for development and demonstrations.

## Architecture

```text
                    ┌───────────────────────────┐
                    │ Synthetic CSV files       │
                    │ Prototype/Data/            │
                    └─────────────┬─────────────┘
                                  │
                                  ▼
                    ┌───────────────────────────┐
                    │ Python graph loader       │
                    │ load_to_neo4j.py          │
                    └─────────────┬─────────────┘
                                  │
                                  ▼
                    ┌───────────────────────────┐
                    │ Neo4j graph database      │
                    └─────────────┬─────────────┘
                                  │
                                  ▼
                    ┌───────────────────────────┐
                    │ FastAPI backend           │◄────► Ollama
                    │ REST endpoints + graph    │       Llama 3.1
                    └─────────────┬─────────────┘
                                  │ HTTP
                                  ▼
                    ┌───────────────────────────┐
                    │ React + Cytoscape.js      │
                    │ Investigation interface  │
                    └───────────────────────────┘
```

## Technology stack

| Layer | Technologies |
|---|---|
| Frontend | React, Vite, JavaScript, Cytoscape.js, Axios |
| Backend | Python, FastAPI, Uvicorn, Pydantic |
| Graph database | Neo4j |
| Natural-language query layer | Ollama, Llama 3.1 8B, read-only Cypher validation |
| Sample data | CSV |
| Containerization | Docker, Docker Compose |

---

## Repository structure

```text
NETRA/
├── README.md
├── docker-compose.yml
├── PPT/
│   ├── NETRA.pdf
│   └── SIH-2026 .pptx
├── Screenshots/
│   ├── Build.png
│   ├── Frontend.png
│   └── Neo4j.png
└── Prototype/
    ├── Prototype.md
    ├── Backend/
    │   ├── Dockerfile
    │   ├── main.py
    │   ├── db.py
    │   ├── graph_utils.py
    │   ├── llm.py
    │   └── requirements.txt
    ├── Data/
    │   ├── persons.csv
    │   ├── phones.csv
    │   ├── bank_accounts.csv
    │   ├── vehicles.csv
    │   ├── cases.csv
    │   ├── call_records.csv
    │   └── transactions.csv
    ├── Graph/
    │   └── load_to_neo4j.py
    └── Frontend/
        ├── package.json
        └── src/
            ├── App.jsx
            ├── GraphView.jsx
            ├── ChatPanel.jsx
            └── api.js
```

---

## Graph data model

### Node types

| Node label | Source file | Main properties |
|---|---|---|
| `Person` | `persons.csv` | `person_id`, `name`, `age`, `gender`, `address`, `city` |
| `Phone` | `phones.csv` | `phone_number` |
| `Account` | `bank_accounts.csv` | `account_id`, `bank_name` |
| `Vehicle` | `vehicles.csv` | `plate_number`, `vehicle_type` |
| `Case` | `cases.csv` | `case_id`, `description`, `location` |

### Relationships

| Relationship | Direction | Meaning |
|---|---|---|
| `OWNS` | `Person → Phone` | Person is associated with a phone |
| `OWNS` | `Person → Account` | Person is associated with a bank account |
| `OWNS` | `Person → Vehicle` | Person is associated with a vehicle |
| `CALLED` | `Phone → Phone` | Call record, including timestamp and duration |
| `TRANSACTED_WITH` | `Account → Account` | Transaction record, including timestamp and amount |
| `INVOLVED_IN` | `Person → Case` | Person is linked to a case in the sample data |

The loader creates nodes first, then relationships between matching records. Case links are read from the comma-separated `linked_person_ids` column in `cases.csv`.

### CSV schemas

| File | Expected columns |
|---|---|
| `persons.csv` | `person_id,name,age,gender,address,city` |
| `phones.csv` | `phone_number,owner_id` |
| `bank_accounts.csv` | `account_id,owner_id,bank_name` |
| `vehicles.csv` | `plate_number,owner_id,vehicle_type` |
| `cases.csv` | `case_id,description,linked_person_ids,location` |
| `call_records.csv` | `caller_number,receiver_number,timestamp,duration_seconds` |
| `transactions.csv` | `from_account,to_account,amount,timestamp` |

---

## Requirements

For a native local setup, install:

- Python 3.11 or a compatible recent Python version
- Node.js and npm
- Neo4j 5.x, running locally
- Ollama and the `llama3.1:8b` model for the AI Assistant (optional for the other graph features)

Make sure Neo4j is reachable at `bolt://localhost:7687`. The default local configuration in the project uses username `neo4j` and password `password123`; change these for your own environment rather than reusing demo credentials.

## Run locally

Run each component in a separate terminal.

### 1. Start Neo4j

Start your Neo4j database and ensure Bolt is listening on `localhost:7687`. Set the database credentials to match the environment variables you will use for the backend and data loader.

Open Neo4j Browser at:

```text
http://localhost:7474
```

### 2. Load the sample data

```bash
cd NETRA/Prototype/Data
python -m pip install neo4j
python ../Graph/load_to_neo4j.py
```

The loader reads the CSV files from the current working directory and loads the records into Neo4j.

**Warning:** The loader calls `MATCH (n) DETACH DELETE n` before importing. This clears **all nodes and relationships in the configured Neo4j database**. Use a dedicated development database and do not run it against data you need to keep.

If your Neo4j credentials differ from the defaults, update the loader configuration in `Prototype/Graph/load_to_neo4j.py` before running it.

### 3. Start the backend

```bash
cd NETRA/Prototype/Backend
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

The API health check is available at `http://localhost:8000/`. Interactive API documentation is at `http://localhost:8000/docs`.

The backend reads these environment variables:

```bash
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="your-password"
export OLLAMA_HOST="http://localhost:11434"
export OLLAMA_MODEL="llama3.1:8b"
```

Set the variables before starting the backend. The values above are examples; they must match your local setup.

### 4. Start Ollama (optional, for AI Assistant)

Install and start Ollama, then pull the model:

```bash
ollama pull llama3.1:8b
ollama serve
```

If Ollama is already running as a background service, you may only need the `ollama pull` command. By default, the backend expects Ollama at `http://localhost:11434`. If you use a different host or port, set `OLLAMA_HOST` accordingly.

### 5. Start the frontend

In another terminal:

```bash
cd NETRA/Prototype/Frontend
npm install
npm run dev
```

Open the local URL printed by Vite, usually `http://localhost:5173`.

The frontend expects the API at `http://localhost:8000`; keep the backend running while using the interface.

### 6. Production build / lint

From `Prototype/Frontend`:

```bash
npm run build
npm run lint
```

---

## Run with Docker Compose

The repository includes a `docker-compose.yml` intended to start Neo4j, load the sample CSVs, run Ollama, and start the FastAPI backend:

```bash
docker compose up --build
```

The first run may take a while because Docker downloads the service images and Ollama downloads the Llama model. The React frontend is run separately for development:

```bash
cd Prototype/Frontend
npm install
npm run dev
```

Then open the Vite URL shown in the terminal.

**Configuration note:** Before relying on the Compose setup, verify that the Ollama service's listening port, health check, and the `OLLAMA_HOST` values used by the Compose services agree. Ollama's default listening port is `11434`; the checked-in Compose file currently references `11435` in several places. Also verify the loader's Neo4j connection settings match the Compose service hostname and credentials. The native setup above lets you configure these explicitly.

To stop the stack:

```bash
docker compose down
```

To stop the stack and remove its persisted database/model volumes as well:

```bash
docker compose down -v
```

The second command permanently removes the Compose-managed Neo4j and Ollama data volumes.

---

## API reference

Base URL for local development: `http://localhost:8000`

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/` | API health check |
| `GET` | `/person/{person_id}` | Return a person's directly connected graph |
| `GET` | `/person/{person_id}/network?depth=2` | Return a person's network up to a specified hop depth (1–4) |
| `GET` | `/cluster/detect` | Detect the most connected group using shared entities |
| `GET` | `/search?name={text}` | Search people by partial name |
| `POST` | `/ask` | Ask a natural-language question about the graph |

### Example requests

Health check:

```bash
curl http://localhost:8000/
```

Search:

```bash
curl "http://localhost:8000/search?name=arun"
```

Load a person's network:

```bash
curl "http://localhost:8000/person/P001/network?depth=2"
```

Detect a cluster:

```bash
curl http://localhost:8000/cluster/detect
```

Ask a natural-language question:

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Which persons are linked to case C004?"}'
```

`POST /ask` accepts a JSON body with a non-empty `question` of up to 500 characters. Its response includes `question`, `cypher`, `answer`, `data`, and `error`. If Ollama is unavailable or the generated query cannot be safely used, inspect the `error` field and ensure the local model service is running.

---

## Frontend workflow

1. Start the backend and database.
2. Open the frontend in your browser.
3. Search for a person by name and select a result to load their network.
4. Use **Detect Cluster** to find and highlight the prototype's most connected group.
5. Open **AI Assistant** to ask questions in plain English.
6. Use **View query** on an AI response to inspect the generated Cypher query.

---

## Configuration

The backend uses environment variables for Neo4j and Ollama connection settings:

| Variable | Default | Purpose |
|---|---|---|
| `NEO4J_URI` | `bolt://localhost:7687` | Neo4j Bolt URI |
| `NEO4J_USER` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | `password123` | Neo4j password |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama base URL |
| `OLLAMA_MODEL` | `llama3.1:8b` | Model name used for natural-language queries |

The data loader currently has its own Neo4j connection configuration in `Prototype/Graph/load_to_neo4j.py`. Keep that configuration in sync with the database you intend to load.

---

## Limitations and safety notes

- The checked-in CSVs are sample/synthetic data and should not be treated as real investigative records.
- Cluster detection is a heuristic based on shared graph entities; it does not establish criminal activity.
- AI-generated Cypher and natural-language explanations can be incorrect or incomplete. Review the query and underlying graph results.
- The natural-language layer is intended to generate read-only queries and includes checks against mutating queries, but it should not be treated as a complete security boundary for a production system.
- Use access controls, appropriate audit logging, secure secrets, data minimization, and a dedicated database before any real-world deployment.
- Do not commit real personal, financial, call-detail, or investigative data, passwords, API keys, or other secrets to this repository.

## Roadmap

Potential areas for future work (not claims about current functionality):

- Stronger graph analytics and community-detection methods
- Temporal analysis of calls and transactions
- More comprehensive entity resolution and duplicate handling
- Role-based access control and audit trails
- Improved validation, testing, and deployment hardening

## Team and project

**NETRA — Network Entity Tracking & Relationship Analysis**  
Smart India Hackathon 2026 · Problem Statement **SIH26189**

This repository contains the project's prototype, sample data, presentation material, and screenshots. Contributions and feedback are welcome.
