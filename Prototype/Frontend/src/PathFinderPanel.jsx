import { useState } from "react";
import { searchPerson, getShortestPath } from "./api";

/**
 * PathFinderPanel — "How is Person A linked to Person B?"
 *
 * The starting person is whichever Person node is currently selected in
 * the graph. The investigator searches for a second person, and the panel
 * asks the backend for the shortest chain between them (GET /path). The
 * chain is then drawn in the graph via onPathFound, and each hop is listed
 * in plain English below.
 */
export default function PathFinderPanel({ fromPersonId, fromLabel, onPathFound, onClear }) {
  const [query, setQuery] = useState("");
  const [matches, setMatches] = useState([]);
  const [searching, setSearching] = useState(false);
  const [result, setResult] = useState(null);
  const [computing, setComputing] = useState(false);
  const [error, setError] = useState(null);

  async function handleSearch(e) {
    e.preventDefault();
    const term = query.trim();
    if (!term) return;
    setSearching(true);
    setError(null);
    try {
      const data = await searchPerson(term);
      // Don't offer the starting person as their own target.
      setMatches(data.results.filter((p) => p.person_id !== fromPersonId));
    } catch (err) {
      setError("Search failed.");
    } finally {
      setSearching(false);
    }
  }

  async function handleChoose(target) {
    setComputing(true);
    setError(null);
    setMatches([]);
    setQuery("");
    try {
      const data = await getShortestPath(fromPersonId, target.person_id);
      setResult({ ...data, toLabel: target.name });
      if (data.found) {
        onPathFound(data.graph, data.person_ids);
      }
    } catch (err) {
      setError("Could not compute a path.");
    } finally {
      setComputing(false);
    }
  }

  function handleClear() {
    setResult(null);
    setMatches([]);
    setQuery("");
    setError(null);
    onClear();
  }

  return (
    <div className="panel path-panel">
      <h3>Find Path</h3>
      <p className="muted path-from">
        From: <strong>{fromLabel}</strong>
      </p>

      <form className="path-search" onSubmit={handleSearch}>
        <input
          type="text"
          placeholder="Search second person..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          disabled={searching || computing}
        />
        <button type="submit" disabled={searching || computing || !query.trim()}>
          {searching ? "..." : "Find"}
        </button>
      </form>

      {error && <p className="error-box">{error}</p>}

      {matches.length > 0 && (
        <ul className="result-list path-matches">
          {matches.map((p) => (
            <li key={p.person_id} onClick={() => handleChoose(p)}>
              <strong>{p.name}</strong>
              <span className="muted"> — {p.city}</span>
            </li>
          ))}
        </ul>
      )}

      {computing && <p className="muted">Tracing chain...</p>}

      {result && !computing && (
        <div className="path-result">
          <p className="path-headline">
            {result.found ? (
              result.hops === 0 ? (
                <>Same person.</>
              ) : (
                <>
                  <strong>{fromLabel}</strong> → <strong>{result.toLabel}</strong>: {result.hops} hop
                  {result.hops === 1 ? "" : "s"}
                </>
              )
            ) : (
              <>No chain found between {fromLabel} and {result.toLabel} within the search depth.</>
            )}
          </p>

          {result.found && result.steps.length > 0 && (
            <ol className="path-steps">
              {result.steps.map((s, i) => (
                <li key={i}>
                  <span className="path-node">{s.from}</span>
                  <span className="path-rel">— {s.relationship} →</span>
                  <span className="path-node">{s.to}</span>
                </li>
              ))}
            </ol>
          )}

          <button className="path-clear" onClick={handleClear}>
            Clear path
          </button>
        </div>
      )}
    </div>
  );
}
