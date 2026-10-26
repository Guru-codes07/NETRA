# NETRA

**Network Entity Tracking & Relationship Analysis**

A graph-based investigation tool for exploring relationships in criminal-case data — built on Neo4j, FastAPI, and React, with a local LLM for natural-language queries and heuristic risk scoring over the network.

> Personal project / portfolio prototype, originally started for SIH 2026 (SIH26189). Runs entirely on synthetic data, fully local — no external APIs, no data leaves your machine.

---

## What it does

- **Visualize networks** — interactive graph of people, phones, bank accounts, vehicles, and cases, with the connections between them
- **Ask questions in plain English** — a local Llama 3.1 model translates natural-language questions into Cypher, runs them against the graph, and explains the results
- **Risk scoring** — every person gets a 0–100 score based on their connections and case involvement, with nodes color-coded red/orange/green
- **Timeline view** — chronological call and transaction history for any selected person
- **Cluster detection** — surfaces the most densely connected group in the graph
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

See [`Prototype/Prototype.md`](Prototype/Prototype.md) for the full technical writeup — architecture diagram, data model, every API endpoint, the exact risk-scoring formula, and an honest list of what is and isn't implemented.

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

Prefer to run each service yourself instead of Docker? See the manual setup in [`Prototype/Prototype.md`](Prototype/Prototype.md#7-setup-instructions).

---

## Project structure

```
NETRA-main/
├── docker-compose.yml
└── Prototype/
    ├── Backend/          # FastAPI app, Neo4j queries, LLM + risk engines
    │   ├── main.py
    │   ├── db.py
    │   ├── llm.py        # natural-language → Cypher, via Ollama
    │   ├── risk.py        # heuristic risk scoring
    │   └── timeline.py    # per-person call/transaction timeline
    ├── Frontend/          # React + Cytoscape UI
    │   └── src/
    ├── Graph/             # CSV → Neo4j loader
    ├── Data/              # synthetic CSV dataset
    ├── Loader/            # Docker build for the one-shot data loader
    └── Prototype.md       # full technical documentation
```

---

## A note on what this is

NETRA is a working prototype over **synthetic** data, built to explore graph-based investigation tooling. The risk score is a hand-written structural heuristic (not a trained ML model), cluster detection is a plain Cypher query (not Neo4j GDS/Louvain), and the AI Assistant translates questions into read-only queries — it doesn't draw conclusions about guilt. None of this is connected to real investigative, banking, or telecom systems. Full honesty section in [`Prototype.md`](Prototype/Prototype.md#8-current-limitations--honest-status).

---

## License

Personal project — no license specified yet.****
