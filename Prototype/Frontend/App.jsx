import { useState } from "react";
import GraphView from "./GraphView";
import { getPersonNetwork, detectCluster, searchPerson } from "./api";
import "./App.css";

export default function App() {
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  const [highlightIds, setHighlightIds] = useState([]);
  const [insight, setInsight] = useState(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleDetectCluster() {
    setLoading(true);
    setError(null);
    setInsight(null);
    try {
      const result = await detectCluster();
      setInsight(result);
      setHighlightIds(result.cluster_person_ids);
      const network = await getPersonNetwork(result.center_person_id, 2);
      setGraphData(network);
    } catch (err) {
      setError("Could not reach the NETRA API. Is the backend running on :8000?");
    } finally {
      setLoading(false);
    }
  }

  async function handleSearch(e) {
    e.preventDefault();
    if (!searchTerm.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const { results } = await searchPerson(searchTerm);
      setSearchResults(results);
    } catch (err) {
      setError("Search failed. Is the backend running on :8000?");
    } finally {
      setLoading(false);
    }
  }

  async function loadPersonNetwork(personId) {
    setLoading(true);
    setError(null);
    setInsight(null);
    setHighlightIds([]);
    try {
      const network = await getPersonNetwork(personId, 2);
      setGraphData(network);
    } catch (err) {
      setError("Could not load network for that person.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-name">NETRA</span>
          <span className="brand-sub">AI-Powered Criminal Network Intelligence Platform</span>
        </div>
        <form className="search-form" onSubmit={handleSearch}>
          <input
            type="text"
            placeholder="Search person by name..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <button type="submit">Search</button>
        </form>
        <button className="detect-btn" onClick={handleDetectCluster} disabled={loading}>
          {loading ? "Analyzing..." : "Detect Cluster"}
        </button>
      </header>

      <div className="body">
        <aside className="sidebar">
          {error && <div className="error-box">{error}</div>}

          {searchResults.length > 0 && (
            <div className="panel">
              <h3>Search Results</h3>
              <ul className="result-list">
                {searchResults.map((p) => (
                  <li key={p.person_id} onClick={() => loadPersonNetwork(p.person_id)}>
                    <strong>{p.name}</strong>
                    <span>{p.person_id} — {p.city}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {insight && (
            <div className="panel insight-panel">
              <h3>AI Insight</h3>
              <p className="insight-headline">
                {insight.connection_count + 1} entities form a highly connected cluster
              </p>
              <p className="insight-text">{insight.explanation}</p>
              <p className="insight-tag">Potentially Significant Network — Requires Investigator Review</p>
            </div>
          )}

          {selectedNode && (
            <div className="panel">
              <h3>Selected Entity</h3>
              <p><strong>{selectedNode.label}</strong></p>
              <p className="muted">{selectedNode.type}</p>
            </div>
          )}

          {!insight && !searchResults.length && !error && (
            <div className="panel muted-panel">
              <p>Search for a person, or click "Detect Cluster" to surface the most densely
              connected group in the network automatically.</p>
            </div>
          )}
        </aside>

        <main className="graph-area">
          {graphData.nodes.length > 0 ? (
            <GraphView
              nodes={graphData.nodes}
              edges={graphData.edges}
              highlightIds={highlightIds}
              onNodeClick={setSelectedNode}
            />
          ) : (
            <div className="empty-state">
              <p>No graph loaded yet.</p>
              <p className="muted">Run a search or detect a cluster to visualize the network.</p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
