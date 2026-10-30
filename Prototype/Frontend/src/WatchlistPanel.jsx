import { useEffect, useState } from "react";
import { getWatchlist } from "./api";

/**
 * WatchlistPanel — lists everyone currently flagged on the watchlist
 * (GET /watchlist). Click a name to load their network. The actual
 * highlighting of watchlisted people inside any graph (search results,
 * cluster view, case view, etc.) happens automatically in GraphView.jsx,
 * since on_watchlist is a plain property on the Person node and flows
 * through every endpoint that returns Person nodes — this panel is just
 * a convenient index, not the highlighting mechanism itself.
 */
export default function WatchlistPanel({ onViewPersonNetwork, refreshKey }) {
  const [people, setPeople] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    getWatchlist()
      .then((data) => setPeople(data.people))
      .catch(() => setError("Could not load watchlist."))
      .finally(() => setLoading(false));
  }, [refreshKey]);

  return (
    <div className="panel">
      <h3>Watchlist</h3>

      {loading && <p className="muted">Loading...</p>}
      {error && <p className="error-box">{error}</p>}

      {!loading && !error && people.length === 0 && (
        <p className="muted">No one on the watchlist yet. Select a person and use "Add to Watchlist".</p>
      )}

      {!loading && !error && people.length > 0 && (
        <ul className="result-list">
          {people.map((p) => (
            <li key={p.person_id} onClick={() => onViewPersonNetwork(p.person_id)}>
              <span className="watchlist-star">★</span>
              <strong>{p.name}</strong>
              <span className="muted"> — {p.city}</span>
              {p.risk_level && (
                <span className={`risk-badge risk-${p.risk_level.toLowerCase()}`}>
                  {p.risk_level}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
