
"""

llm.py — Natural-language query layer for NETRA, backed by a local
Llama 3.1 model served through Ollama.

"""
from __future__ import annotations

import json
import logging
import re

import requests

from db import run_query

logger = logging.getLogger("netra.llm")


# Configuration

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.1:8b"
REQUEST_TIMEOUT_SECONDS = 60

_WRITE_KEYWORDS = (
    "CREATE", "MERGE", "DELETE", "DETACH", "SET",
    "REMOVE", "DROP", "CALL {", "LOAD CSV",
)

# Schema description given to the model so it can write valid Cypher
# against NETRA's actual graph. Keep this in sync with
# Prototype/Graph/load_to_neo4j.py if the data model changes.
GRAPH_SCHEMA = """
Node labels and properties:
  (:Person {person_id, name, age, gender, address, city})
  (:Phone {phone_number})
  (:Account {account_id, bank_name})
  (:Vehicle {plate_number, vehicle_type})
  (:Case {case_id, description, location})

Relationships:
  (:Person)-[:OWNS]->(:Phone)
  (:Person)-[:OWNS]->(:Account)
  (:Person)-[:OWNS]->(:Vehicle)
  (:Person)-[:INVOLVED_IN]->(:Case)
  (:Phone)-[:CALLED {timestamp, duration_seconds}]->(:Phone)
  (:Account)-[:TRANSACTED_WITH {timestamp, amount}]->(:Account)
""".strip()

_CYPHER_SYSTEM_PROMPT = f"""You are a Cypher query generator for a Neo4j criminal-investigation graph database named NETRA.

{GRAPH_SCHEMA}

Rules:
- Output ONLY a single valid Cypher query. No explanation, no markdown fences, no commentary.
- The query must be read-only (MATCH / WHERE / RETURN / OPTIONAL MATCH / WITH / ORDER BY / LIMIT only).
- Never use CREATE, MERGE, DELETE, SET, REMOVE, or DROP.
- Always include a RETURN clause.
- Limit results to 50 rows unless the question clearly needs fewer.
- Use `toLower()` and `CONTAINS` for fuzzy name/text matching instead of exact equality.
"""

_EXPLAIN_SYSTEM_PROMPT = """You are an assistant for a criminal-investigation graph platform called NETRA.
Explain the given query result to an investigator in 2-4 plain-English sentences.
Be factual and specific, citing names, ids, and counts present in the data.
Do not speculate beyond the data. Do not accuse anyone of a crime — describe
connections and patterns only; final judgment is left to the investigator.
If the result is empty, say plainly that nothing matching the question was found.
"""



# Exceptions


class LLMServiceError(Exception):
    """Raised when Ollama is unreachable or returns an unusable response."""


class UnsafeQueryError(Exception):
    """Raised when the model generates a query that would mutate the graph."""



# Ollama client
def _call_ollama(prompt: str, system: str) -> str:
    """
    Send a single prompt to the local Ollama server and return the
    generated text. Uses the non-streaming /api/generate endpoint for
    simplicity — the backend waits for the full response before replying.
    """
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {"temperature": 0.1},  # low temperature: we want precise Cypher, not creativity
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.exceptions.ConnectionError as exc:
        raise LLMServiceError(
            "Could not reach Ollama at localhost:11434. Is it running? Try: ollama serve"
        ) from exc
    except requests.exceptions.Timeout as exc:
        raise LLMServiceError("Ollama took too long to respond.") from exc
    except requests.exceptions.HTTPError as exc:
        raise LLMServiceError(f"Ollama returned an error: {exc}") from exc

    try:
        return response.json()["response"].strip()
    except (KeyError, json.JSONDecodeError) as exc:
        raise LLMServiceError("Ollama returned an unexpected response shape.") from exc



# Cypher generation
def _strip_code_fences(text: str) -> str:
    """Remove ``` / ```cypher fences the model sometimes adds despite instructions."""
    cleaned = re.sub(r"^```(?:cypher)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)
    return cleaned.strip()


def _validate_read_only(query: str) -> None:
    """Raise UnsafeQueryError if the query contains any write keyword."""
    upper = query.upper()
    for keyword in _WRITE_KEYWORDS:
        if keyword in upper:
            raise UnsafeQueryError(f"Generated query contains a disallowed write operation: {keyword}")
    if "RETURN" not in upper:
        raise UnsafeQueryError("Generated query has no RETURN clause.")


def generate_cypher(question: str) -> str:
    """Translate a natural-language investigator question into a validated Cypher query."""
    raw = _call_ollama(prompt=question, system=_CYPHER_SYSTEM_PROMPT)
    cypher = _strip_code_fences(raw)
    _validate_read_only(cypher)
    return cypher



# Result explanation
def explain_result(question: str, cypher: str, rows: list[dict]) -> str:
    """Turn raw Cypher result rows into a short, plain-English explanation."""
    prompt = (
        f"Investigator's question: {question}\n\n"
        f"Cypher query used: {cypher}\n\n"
        f"Query result (JSON): {json.dumps(rows, default=str)[:4000]}"
    )
    return _call_ollama(prompt=prompt, system=_EXPLAIN_SYSTEM_PROMPT)



# Public orchestrator

def ask_question(question: str) -> dict:
    """
    Full NL-query pipeline: question -> Cypher -> Neo4j -> explanation.

    Returns a dict shaped for direct JSON response from the API:
        {
            "question": str,
            "cypher": str | None,
            "answer": str,
            "data": list[dict],
            "error": str | None,
        }

    Never raises — all failure modes are caught and surfaced in "error"
    so the FastAPI endpoint can return a 200 with a useful message
    instead of a bare 500.
    """
    cypher = None
    try:
        cypher = generate_cypher(question)
        logger.info("Generated Cypher for question %r: %s", question, cypher)

        rows = run_query(cypher)
        answer = explain_result(question, cypher, rows)

        return {
            "question": question,
            "cypher": cypher,
            "answer": answer,
            "data": rows,
            "error": None,
        }

    except UnsafeQueryError as exc:
        logger.warning("Rejected unsafe generated query for %r: %s", question, exc)
        return {
            "question": question,
            "cypher": cypher,
            "answer": "I couldn't safely answer that question — the generated query attempted to modify the graph, which isn't permitted.",
            "data": [],
            "error": str(exc),
        }

    except LLMServiceError as exc:
        logger.error("LLM service error for %r: %s", question, exc)
        return {
            "question": question,
            "cypher": cypher,
            "answer": "The AI assistant is currently unavailable.",
            "data": [],
            "error": str(exc),
        }

    except Exception as exc:  # Neo4j syntax errors, etc. — surface, don't crash the API
        logger.exception("Unexpected error answering question %r", question)
        return {
            "question": question,
            "cypher": cypher,
            "answer": "I couldn't run that query against the graph. Try rephrasing the question.",
            "data": [],
            "error": str(exc),
        }
