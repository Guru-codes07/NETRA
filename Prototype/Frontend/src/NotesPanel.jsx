import { useEffect, useState } from "react";
import { getNotes, addNote, deleteNote } from "./api";

/**
 * NotesPanel — free-text annotations on whichever entity is currently
 * selected (any type: Person, Phone, Account, Vehicle, Case). Backed by
 * GET/POST /entities/{type}/{id}/notes and DELETE /notes/{note_id}
 * (see notes.py). Self-contained: fetches its own notes whenever the
 * entityType/entityId props change.
 */
export default function NotesPanel({ entityType, entityId, entityLabel }) {
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getNotes(entityType, entityId)
      .then((data) => { if (!cancelled) setNotes(data.notes); })
      .catch(() => { if (!cancelled) setError("Could not load notes."); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [entityType, entityId]);

  async function handleAdd(e) {
    e.preventDefault();
    const text = draft.trim();
    if (!text || saving) return;
    setSaving(true);
    try {
      const note = await addNote(entityType, entityId, text);
      setNotes((prev) => [note, ...prev]);
      setDraft("");
    } catch (err) {
      setError("Could not save note.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(noteId) {
    try {
      await deleteNote(noteId);
      setNotes((prev) => prev.filter((n) => n.note_id !== noteId));
    } catch (err) {
      setError("Could not delete note.");
    }
  }

  return (
    <div className="panel">
      <h3>Notes — {entityLabel}</h3>

      <form className="notes-form" onSubmit={handleAdd}>
        <textarea
          placeholder="Add a note..."
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          rows={2}
          disabled={saving}
        />
        <button type="submit" disabled={saving || !draft.trim()}>
          {saving ? "Saving..." : "Add Note"}
        </button>
      </form>

      {loading && <p className="muted">Loading notes...</p>}
      {error && <p className="error-box">{error}</p>}

      {!loading && !error && notes.length === 0 && (
        <p className="muted">No notes yet.</p>
      )}

      {!loading && notes.length > 0 && (
        <ul className="notes-list">
          {notes.map((n) => (
            <li key={n.note_id} className="notes-item">
              <p className="notes-text">{n.text}</p>
              <div className="notes-meta">
                <span>{new Date(n.created_at).toLocaleString()}</span>
                <button className="notes-delete" onClick={() => handleDelete(n.note_id)}>Delete</button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
