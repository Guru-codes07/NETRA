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
