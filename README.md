# NETRA

**Network Entity Tracking & Relationship Analysis**

A graph-based investigation tool for exploring relationships in criminal-case data — built on Neo4j, FastAPI, and React, with a local LLM for natural-language queries, heuristic risk scoring, and a full investigator workflow (cases, watchlist, notes) layered on top of the network.

> Personal project / portfolio prototype, originally started for SIH 2026 (SIH26189). Runs entirely on synthetic data, fully local — no external APIs, no data leaves your machine.

---

## What it does

- **Visualize networks** — interactive graph of people, phones, bank accounts, vehicles, and cases, with the connections between them
- **Ask questions in plain English** — a local Llama 3.1 model translates natural-language questions into Cypher, runs them against the graph, and explains the results
- **Risk scoring** — every person gets a 0–100 score based on their connections and case involvement, with nodes color-coded red/orange/green
- **Timeline view** — chronological call and transaction history for any selected person
- **Cluster detection** — surfaces the most densely connected group in the graph
- **Case view** — browse every case, see who's linked to it, their risk scores, and the phones/accounts/vehicles tied to those people
- **Dashboard** — a landing page with entity counts, risk distribution, the most-connected people, and the busiest cases
- **Watchlist** — flag specific people so they stay highlighted with a gold ring in *every* graph view, however you reach them — search, cluster detection, or case view
- **Notes** — attach free-text, timestamped notes to any person, phone, account, vehicle, or case
- **Export** — download the current view as CSV, or generate a printable PDF report

---

## Stack

| | |
|---|---|
| Graph database | Neo4j 5.24 |
| Backend | FastAPI (Python 3.11) |
| AI | Llama 3.1 8B via Ollama (local, no external API) |
| Frontend | React 19 + Cytoscape.js (Vite) |
| Orchestration | Docker Compose |

See [`Prototype/Prototype.md`](Prototype/Prototype.md) for the full technical writeup — architecture, data model, and an honest list of what is and isn't implemented. (Note: that document predates the Case View / Dashboard / Watchlist / Notes features below and is due for an update to match.)

---

## Quick start

**Requirements:** Docker + Docker Compose, Node.js + npm

```bash
# 1. Start Neo4j, load the data, start Ollama, pull the model, start the backend
docker-compose up --build

# 2. In a separate terminal — the frontend
cd Prototype/Frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

First run takes a few minutes (pulling the Neo4j/Ollama images and the ~4.7GB Llama model). Every run after that is fast.

---

## API overview

22 endpoints, grouped by area — full detail in [`Prototype.md`](Prototype/Prototype.md):

| Area | Endpoints |
|---|---|
| Core graph | `GET /person/{id}`, `GET /person/{id}/network`, `GET /cluster/detect`, `GET /search` |
| AI Assistant | `POST /ask` |
| Risk scoring | `POST /risk/precompute`, `GET /risk/{id}` |
| Timeline | `GET /person/{id}/timeline` |
| Cases | `GET /cases`, `GET /cases/{id}` |
| Dashboard | `GET /dashboard` |
| Watchlist | `GET /watchlist`, `POST /watchlist/{id}`, `DELETE /watchlist/{id}` |
| Notes | `GET /entities/{type}/{id}/notes`, `POST /entities/{type}/{id}/notes`, `DELETE /notes/{id}` |

---

## Project structure

```
NETRA-main/
├── docker-compose.yml
└── Prototype/
    ├── Backend/
    │   ├── main.py         # FastAPI app, all routes
    │   ├── db.py            # Neo4j connection
    │   ├── llm.py            # natural-language → Cypher, via Ollama
    │   ├── risk.py            # heuristic risk scoring
    │   ├── timeline.py         # per-person call/transaction timeline
    │   ├── cases.py             # case list + detail
    │   ├── dashboard.py          # landing-page summary stats
    │   ├── watchlist.py           # flag/unflag/list watchlisted people
    │   └── notes.py                 # free-text notes on any entity
    ├── Frontend/
    │   └── src/
    │       ├── App.jsx              # view switcher + main layout
    │       ├── GraphView.jsx         # Cytoscape graph, risk/watchlist styling
    │       ├── ChatPanel.jsx          # AI Assistant
    │       ├── TimelinePanel.jsx       # per-person timeline
    │       ├── CasesPage.jsx            # case browser
    │       ├── DashboardPage.jsx         # landing page
    │       ├── WatchlistPanel.jsx         # sidebar watchlist list
    │       ├── NotesPanel.jsx              # notes on the selected entity
    │       └── exportUtils.js               # CSV/PDF export
    ├── Graph/              # CSV → Neo4j loader
    ├── Data/                # synthetic CSV dataset
    ├── Loader/                # Docker build for the one-shot data loader
    └── Prototype.md             # detailed technical documentation
```

---

## A note on what this is

NETRA is a working prototype over **synthetic** data, built to explore graph-based investigation tooling. The risk score is a hand-written structural heuristic (not a trained ML model), cluster detection is a plain Cypher query (not Neo4j GDS/Louvain), "linked entities" in the Case view stands in for evidence since the dataset has no dedicated evidence type, and the AI Assistant translates questions into read-only queries — it doesn't draw conclusions about guilt. None of this is connected to real investigative, banking, or telecom systems.

---

## Known gaps

- Dashboard's "busiest cases" list switches to Case View but doesn't yet auto-select that specific case
- No automated test suite or CI pipeline yet
- No authentication — this is a local single-user prototype

---

## License

Personal project — no license specified yet.
