import { useState } from "react";
import GraphView from "./GraphView";
import ChatPanel from "./ChatPanel";
import { getPersonNetwork, detectCluster, searchPerson, precomputeRisk, getPersonRisk } from "./api";
import TimelinePanel from "./TimelinePanel";
import { exportNodesAsCSV, exportReportAsPDF } from "./exportUtils";
import "./App.css";

// Properties already shown elsewhere in the sidebar (risk badge, internal
// ids) — excluded from the generic property list so nothing is duplicated.
const DETAIL_HIDDEN_PROPS = new Set(["risk_score", "risk_level", "person_id"]);

export default function App() {
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  const [highlightIds, setHighlightIds] = useState([]);
  const [insight, setInsight] = useState(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [chatOpen, setChatOpen] = useState(false);
  const [currentPersonId, setCurrentPersonId] = useState(null);
  const [riskSummary, setRiskSummary] = useState(null);
  const [riskLoading, setRiskLoading] = useState(false);
  const [timelineFor, setTimelineFor] = useState(null); // { personId, personName } | null

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
      setCurrentPersonId(result.center_person_id);
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
      setCurrentPersonId(personId);
    } catch (err) {
      setError("Could not load network for that person.");
    } finally {
      setLoading(false);
    }
  }

  async function handlePrecomputeRisk() {
    setRiskLoading(true);
    setError(null);
    try {
      const result = await precomputeRisk();
      setRiskSummary(result);
      // Refresh the currently displayed graph so nodes pick up the
      // newly-written risk_score/risk_level properties and recolor.
      if (currentPersonId) {
        const network = await getPersonNetwork(currentPersonId, 2);
        setGraphData(network);
      }
    } catch (err) {
      setError("Could not compute risk scores. Is the backend running on :8000?");
    } finally {
      setRiskLoading(false);
    }
  }

  async function handleNodeClick(nodeData) {
    setSelectedNode(nodeData);
    setTimelineFor(null); // selecting a different node closes any open timeline
    if (nodeData.type !== "Person" || !nodeData.personId) return;

    // On-demand risk lookup for whichever person was just clicked —
    // works even if "Compute Risk Scores" hasn't been run yet this session.
    try {
      const risk = await getPersonRisk(nodeData.personId);
      setSelectedNode((prev) =>
        prev && prev.id === nodeData.id ? { ...prev, riskScore: risk.risk_score, riskLevel: risk.risk_level } : prev
      );
      setGraphData((prev) => ({
        ...prev,
        nodes: prev.nodes.map((n) =>
          n.id === nodeData.id
            ? { ...n, properties: { ...n.properties, risk_score: risk.risk_score, risk_level: risk.risk_level } }
            : n
        ),
      }));
    } catch (err) {
      // Risk lookup failing shouldn't block viewing the node's basic info.
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
        <button className="detect-btn" onClick={handlePrecomputeRisk} disabled={riskLoading}>
          {riskLoading ? "Scoring..." : "Compute Risk Scores"}
        </button>
        <button className="ai-toggle-btn" onClick={() => setChatOpen((v) => !v)}>
          {chatOpen ? "Close AI" : "AI Assistant"}
        </button>
        <button
          className="detect-btn"
          onClick={() => exportNodesAsCSV(graphData.nodes)}
          disabled={graphData.nodes.length === 0}
        >
          Export CSV
        </button>
        <button
          className="detect-btn"
          onClick={() => exportReportAsPDF(graphData.nodes, riskSummary)}
          disabled={graphData.nodes.length === 0}
        >
          Export PDF
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
              {selectedNode.riskLevel && (
                <p className={`risk-badge risk-${selectedNode.riskLevel.toLowerCase()}`}>
                  {selectedNode.riskLevel} Risk — {selectedNode.riskScore}/100
                </p>
              )}

              {selectedNode.properties && Object.keys(selectedNode.properties).length > 0 && (
                <ul className="detail-list">
                  {Object.entries(selectedNode.properties)
                    .filter(([key]) => !DETAIL_HIDDEN_PROPS.has(key))
                    .map(([key, value]) => (
                      <li key={key}>
                        <span className="detail-key">{key.replace(/_/g, " ")}</span>
                        <span className="detail-value">{String(value)}</span>
                      </li>
                    ))}
                </ul>
              )}

              {selectedNode.type === "Person" && selectedNode.personId && (
                <button
                  className="timeline-btn"
                  onClick={() =>
                    setTimelineFor({ personId: selectedNode.personId, personName: selectedNode.label })
                  }
                >
                  View Timeline
                </button>
              )}
            </div>
          )}

          {timelineFor && (
            <TimelinePanel
              personId={timelineFor.personId}
              personName={timelineFor.personName}
              onClose={() => setTimelineFor(null)}
            />
          )}

          {riskSummary && (
            <div className="panel insight-panel">
              <h3>Risk Scoring Complete</h3>
              <p className="insight-text">
                Scored {riskSummary.scored_count} people. Top 5 highest risk:
              </p>
              <ul className="result-list">
                {riskSummary.top_5_highest_risk.map((r) => (
                  <li key={r.person_id} onClick={() => loadPersonNetwork(r.person_id)}>
                    <strong>{r.name}</strong>
                    <span className={`risk-badge risk-${r.risk_level.toLowerCase()}`}>
                      {r.risk_level} — {r.risk_score}/100
                    </span>
                  </li>
                ))}
              </ul>
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
              onNodeClick={handleNodeClick}
            />
          ) : (
            <div className="empty-state">
              <p>No graph loaded yet.</p>
              <p className="muted">Run a search or detect a cluster to visualize the network.</p>
            </div>
          )}
        </main>
      </div>

      <ChatPanel open={chatOpen} onClose={() => setChatOpen(false)} />
    </div>
  );
}
