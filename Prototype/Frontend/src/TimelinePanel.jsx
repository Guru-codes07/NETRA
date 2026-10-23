import { useEffect, useState } from "react";
import { getPersonTimeline } from "./api";

/**
 * TimelinePanel — chronological list of a person's call + transaction
 * activity, merged from GET /person/{id}/timeline (see timeline.py).
 * Rendered inline in the sidebar, styled with the app's existing
 * panel/result-list classes so it matches the rest of the UI.
 */
export default function TimelinePanel({ personId, personName, onClose }) {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    getPersonTimeline(personId)
      .then((data) => {
        if (!cancelled) setEvents(data.events);
      })
      .catch(() => {
        if (!cancelled) setError("Could not load timeline for this person.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [personId]);

  return (
    <div className="panel">
      <div className="panel-header-row">
        <h3>Timeline — {personName}</h3>
        <button className="panel-close" onClick={onClose} aria-label="Close timeline">✕</button>
      </div>

      {loading && <p className="muted">Loading activity...</p>}
      {error && <p className="error-box">{error}</p>}

      {!loading && !error && events.length === 0 && (
        <p className="muted">No call or transaction activity found for this person.</p>
      )}

      {!loading && !error && events.length > 0 && (
        <ul className="timeline-list">
          {events.map((ev, i) => (
            <li key={i} className={`timeline-item timeline-${ev.event_type}`}>
              <span className="timeline-icon">{ev.event_type === "call" ? "📞" : "💸"}</span>
              <div className="timeline-body">
                <div className="timeline-main">
                  {ev.event_type === "call" ? (
                    <>Call {ev.self_entity} → {ev.counterparty} ({ev.duration_seconds}s)</>
                  ) : (
                    <>Transfer {ev.self_entity} → {ev.counterparty} (₹{Number(ev.amount).toLocaleString()})</>
                  )}
                </div>
                <div className="timeline-timestamp">{ev.timestamp}</div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
