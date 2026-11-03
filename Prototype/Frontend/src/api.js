/**
 * api.js — thin wrapper around the NETRA FastAPI backend.
 * Assumes the backend is running at http://localhost:8000
 * (see ../../backend/main.py).
 */

import axios from "axios";

const API_BASE = "http://localhost:8000";

const client = axios.create({ baseURL: API_BASE });

export async function getPersonNetwork(personId, depth = 2) {
  const res = await client.get(`/person/${personId}/network`, {
    params: { depth },
  });
  return res.data; // { nodes: [...], edges: [...] }
}

export async function getPerson(personId) {
  const res = await client.get(`/person/${personId}`);
  return res.data;
}

export async function detectCluster() {
  const res = await client.get(`/cluster/detect`);
  return res.data;
}

export async function searchPerson(name) {
  const res = await client.get(`/search`, { params: { name } });
  return res.data; // { count, results: [...] }
}

export async function askQuestion(question) {
  const res = await client.post(`/ask`, { question });
  return res.data; // { question, cypher, answer, data, error }
}

export async function precomputeRisk() {
  const res = await client.post(`/risk/precompute`);
  return res.data; // { scored_count, top_5_highest_risk: [...] }
}

export async function getPersonRisk(personId) {
  const res = await client.get(`/risk/${personId}`);
  return res.data; // { person_id, name, risk_score, risk_level, degree, case_count }
}

export async function getPersonTimeline(personId) {
  const res = await client.get(`/person/${personId}/timeline`);
  return res.data; // { person_id, event_count, events: [...] }
}

export async function getAllCases() {
  const res = await client.get(`/cases`);
  return res.data; // { cases: [...] }
}

export async function getCaseDetail(caseId) {
  const res = await client.get(`/cases/${caseId}`);
  return res.data; // { case_id, description, location, persons: [...], linked_entities: [...] }
}

export async function getDashboardSummary() {
  const res = await client.get(`/dashboard`);
  return res.data; // { counts, risk_distribution, scored_person_count, most_connected, busiest_cases }
}

export async function getWatchlist() {
  const res = await client.get(`/watchlist`);
  return res.data; // { people: [...] }
}

export async function addToWatchlist(personId) {
  const res = await client.post(`/watchlist/${personId}`);
  return res.data; // { person_id, name, on_watchlist }
}

export async function removeFromWatchlist(personId) {
  const res = await client.delete(`/watchlist/${personId}`);
  return res.data; // { person_id, name, on_watchlist }
}

export async function getNotes(entityType, entityId) {
  const res = await client.get(`/entities/${entityType}/${entityId}/notes`);
  return res.data; // { notes: [...] }
}

export async function addNote(entityType, entityId, text) {
  const res = await client.post(`/entities/${entityType}/${entityId}/notes`, { text });
  return res.data; // { note_id, text, created_at }
}

export async function deleteNote(noteId) {
  const res = await client.delete(`/notes/${noteId}`);
  return res.data; // { deleted, note_id }
}
