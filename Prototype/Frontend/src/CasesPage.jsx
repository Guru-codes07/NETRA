import { useEffect, useState } from "react";
import { getAllCases, getCaseDetail } from "./api";

/**
 * CasesPage — dedicated case-browsing view. Lists every case, and on
 * selecting one shows its linked persons (with risk scores, if computed)
 * and the phones/accounts/vehicles those persons own, which stands in
 * for "evidence" since the dataset has no dedicated evidence entity
 * (see cases.py for that note).
 */
export default function CasesPage({ onViewPersonNetwork }) {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [selectedCaseId, setSelectedCaseId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    getAllCases()
      .then((data) => setCases(data.cases))
      .catch(() => setError("Could not load cases. Is the backend running on :8000?"))
      .finally(() => setLoading(false));
  }, []);

  function handleSelectCase(caseId) {
    setSelectedCaseId(caseId);
    setDetail(null);
    setDetailLoading(true);
    getCaseDetail(caseId)
      .then(setDetail)
      .catch(() => setError("Could not load case detail."))
      .finally(() => setDetailLoading(false));
  }

  return (
    <div className="cases-page">
      <div className="cases-list-col">
        <h2>Cases</h2>
        {loading && <p className="muted">Loading cases...</p>}
        {error && <p className="error-box">{error}</p>}

        {!loading && !error && (
          <ul className="cases-list">
            {cases.map((c) => (
              <li
                key={c.case_id}
                className={c.case_id === selectedCaseId ? "cases-list-item active" : "cases-list-item"}
                onClick={() => handleSelectCase(c.case_id)}
              >
                <div className="cases-list-id">{c.case_id}</div>
                <div className="cases-list-desc">{c.description}</div>
                <div className="cases-list-meta">
                  <span>{c.location}</span>
                  <span>{c.linked_person_count} linked {c.linked_person_count === 1 ? "person" : "people"}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="cases-detail-col">
        {!selectedCaseId && <p className="muted">Select a case to see linked people and entities.</p>}

        {selectedCaseId && detailLoading && <p className="muted">Loading case detail...</p>}

        {detail && !detailLoading && (
          <>
            <h2>{detail.case_id}</h2>
            <p className="cases-detail-desc">{detail.description}</p>
            <p className="muted">{detail.location}</p>

            <h3>Linked Persons ({detail.persons.length})</h3>
            {detail.persons.length === 0 && <p className="muted">No persons linked to this case.</p>}
            <ul className="result-list">
              {detail.persons.map((p) => (
                <li key={p.person_id} onClick={() => onViewPersonNetwork(p.person_id)}>
                  <strong>{p.name}</strong>
                  <span className="muted"> — {p.city}, age {p.age}</span>
                  {p.risk_level && (
                    <span className={`risk-badge risk-${p.risk_level.toLowerCase()}`}>
                      {p.risk_level} — {p.risk_score}/100
                    </span>
                  )}
                </li>
              ))}
            </ul>

            <h3>Linked Entities ({detail.linked_entities.length})</h3>
            <p className="muted cases-evidence-note">
              Phones, accounts, and vehicles owned by linked persons — the closest proxy for
              case evidence in this dataset.
            </p>
            {detail.linked_entities.length === 0 && <p className="muted">No linked entities found.</p>}
            <ul className="detail-list">
              {detail.linked_entities.map((e, i) => (
                <li key={i}>
                  <span className="detail-key">{e.entity_type} · {e.person_name}</span>
                  <span className="detail-value">
                    {e.entity_id}{e.entity_detail ? ` (${e.entity_detail})` : ""}
                  </span>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </div>
  );
}
