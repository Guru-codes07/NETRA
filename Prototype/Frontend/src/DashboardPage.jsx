import { useEffect, useState } from "react";
import { getDashboardSummary } from "./api";

/**
 * DashboardPage — landing page summarizing the whole graph: entity
 * counts, risk-level distribution, the most-connected people, and the
 * busiest cases. Pure read view; clicking a person or case jumps into
 * the graph/case view via the callbacks passed down from App.jsx.
 */
export default function DashboardPage({ onViewPersonNetwork, onViewCase }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    getDashboardSummary()
      .then(setData)
      .catch(() => setError("Could not load dashboard. Is the backend running on :8000?"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="dashboard-page"><p className="muted">Loading dashboard...</p></div>;
  if (error) return <div className="dashboard-page"><p className="error-box">{error}</p></div>;

  const { counts, risk_distribution, scored_person_count, most_connected, busiest_cases } = data;

  const statCards = [
    { label: "Persons", value: counts.persons },
    { label: "Phones", value: counts.phones },
    { label: "Accounts", value: counts.accounts },
    { label: "Vehicles", value: counts.vehicles },
    { label: "Cases", value: counts.cases },
    { label: "Calls", value: counts.calls },
    { label: "Transactions", value: counts.transactions },
  ];

  const maxRisk = Math.max(risk_distribution.High, risk_distribution.Medium, risk_distribution.Low, 1);

  return (
    <div className="dashboard-page">
      <h2>Overview</h2>

      <div className="dashboard-stats-grid">
        {statCards.map((s) => (
          <div className="dashboard-stat-card" key={s.label}>
            <div className="dashboard-stat-value">{s.value}</div>
            <div className="dashboard-stat-label">{s.label}</div>
          </div>
        ))}
      </div>

      <div className="dashboard-columns">
        <div className="dashboard-col">
          <h3>Risk Distribution</h3>
          {scored_person_count === 0 ? (
            <p className="muted">
              No risk scores computed yet. Run "Compute Risk Scores" from the graph view first.
            </p>
          ) : (
            <div className="risk-bar-chart">
              {["High", "Medium", "Low"].map((level) => (
                <div className="risk-bar-row" key={level}>
                  <span className={`risk-bar-label risk-${level.toLowerCase()}`}>{level}</span>
                  <div className="risk-bar-track">
                    <div
                      className={`risk-bar-fill risk-bar-fill-${level.toLowerCase()}`}
                      style={{ width: `${(risk_distribution[level] / maxRisk) * 100}%` }}
                    />
                  </div>
                  <span className="risk-bar-count">{risk_distribution[level]}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="dashboard-col">
          <h3>Most Connected People</h3>
          <ul className="result-list">
            {most_connected.map((p) => (
              <li key={p.person_id} onClick={() => onViewPersonNetwork(p.person_id)}>
                <strong>{p.name}</strong>
                <span className="muted"> — {p.degree} connections</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="dashboard-col">
          <h3>Busiest Cases</h3>
          <ul className="result-list">
            {busiest_cases.map((c) => (
              <li key={c.case_id} onClick={() => onViewCase(c.case_id)}>
                <strong>{c.case_id}</strong>
                <span className="muted"> — {c.linked_person_count} linked people</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
