import { useEffect, useState } from "react";
import { api } from "../api";
import { useToast } from "./Toast.jsx";
import ScoreRing from "./ScoreRing.jsx";

const SUBSCORE_LABELS = {
  skills: "Skills coverage",
  experience: "Experience",
  projects: "Project relevance",
  education: "Education",
  certifications: "Certifications",
};

const FEEDBACK_OPTIONS = [
  { value: "", label: "Feedback (optional)" },
  { value: "relevant", label: "Relevant" },
  { value: "not_relevant", label: "Not relevant" },
  { value: "missing_required_skill", label: "Missing required skill" },
];

export default function CandidateModal({ candidate, onClose, onDecision }) {
  const toast = useToast();
  const [status, setStatus] = useState(candidate.status || "pending");
  const [feedback, setFeedback] = useState(candidate.recruiter_feedback || "");
  const [note, setNote] = useState(candidate.recruiter_note || "");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const explanation = candidate.explanation || {};
  const missingRequired = explanation.missing_required || [];
  const missingNice = explanation.missing_nice_to_have || [];

  const save = async (nextStatus) => {
    setSaving(true);
    try {
      const body = { status: nextStatus ?? status, feedback, note };
      await api.post(`/api/results/${candidate.result_id}/decision`, body);
      setStatus(nextStatus ?? status);
      const labels = { shortlisted: "Shortlisted", pending: "Kept in review", rejected: "Rejected" };
      toast("Decision saved", `${candidate.candidate_name} — ${labels[body.status]}`, "success");
      onDecision?.();
      onClose();
    } catch (err) {
      toast("Could not save decision", err.message, "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" role="dialog" aria-modal="true">
        <div className="modal-head">
          <div className="row">
            <ScoreRing score={candidate.score} size={62} />
            <div>
              <h2>{candidate.candidate_name}</h2>
              <div className="small dim">
                Rank #{candidate.rank} · {candidate.experience_years} yr(s) experience · {candidate.filename}
              </div>
            </div>
          </div>
          <button className="close-x" onClick={onClose} aria-label="Close">✕</button>
        </div>

        <div className="modal-body">
          <div className="card card-pad">
            <div className="card-title"><h3>Match breakdown</h3><span className="chip">{Math.round(candidate.score)}% weighted</span></div>
            {Object.entries(SUBSCORE_LABELS)
              .filter(([key]) => candidate.subscores && key in candidate.subscores)
              .map(([key, label]) => (
                <div className="subbar" key={key}>
                  <span>{label}</span>
                  <div className="progress"><div style={{ width: `${Math.round((candidate.subscores[key] || 0) * 100)}%` }} /></div>
                  <span className="mono">{Math.round((candidate.subscores[key] || 0) * 100)}%</span>
                </div>
              ))}
          </div>

          <div className="grid-2">
            <div className="card card-pad">
              <h3>Why this candidate matched</h3>
              {(explanation.why_matched || []).length === 0 && <p className="dim small">No direct requirement matches were found.</p>}
              {(explanation.why_matched || []).map((why, i) => (
                <p key={i} className="small" style={{ marginTop: 8 }}>✓ {why}</p>
              ))}
              {(explanation.evidence || []).length > 0 && (
                <>
                  <h3 style={{ marginTop: 14 }}>Evidence from the resume</h3>
                  {explanation.evidence.map((quote, i) => (
                    <div className="evidence" key={i}>“{quote}”</div>
                  ))}
                </>
              )}
            </div>

            <div className="card card-pad">
              <h3>Gaps</h3>
              {missingRequired.length === 0 && missingNice.length === 0 && (
                <p className="small dim">No gaps — every detected requirement is covered.</p>
              )}
              {missingRequired.length > 0 && (
                <div style={{ marginTop: 8 }}>
                  <div className="small dim" style={{ marginBottom: 6 }}>Missing required skills</div>
                  <div className="jd-chip-list">
                    {missingRequired.map((s) => <span className="chip red" key={s}>{s}</span>)}
                  </div>
                </div>
              )}
              {missingNice.length > 0 && (
                <div style={{ marginTop: 12 }}>
                  <div className="small dim" style={{ marginBottom: 6 }}>Nice-to-haves not found</div>
                  <div className="jd-chip-list">
                    {missingNice.map((s) => <span className="chip amber" key={s}>{s}</span>)}
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="card card-pad">
            <h3>Your review</h3>
            <p className="small dim" style={{ margin: "4px 0 12px" }}>
              Your decision is stored separately from the AI score and never overwrites it.
            </p>
            <div className="grid-2">
              <div className="field">
                <label>Recruiter feedback</label>
                <select value={feedback} onChange={(e) => setFeedback(e.target.value)}>
                  {FEEDBACK_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
              <div className="field">
                <label>Note</label>
                <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Optional note for your team" />
              </div>
            </div>
            <div className="row" style={{ flexWrap: "wrap" }}>
              <button className="btn btn-success" disabled={saving} onClick={() => save("shortlisted")}>✓ Shortlist</button>
              <button className="btn" disabled={saving} onClick={() => save("pending")}>Keep reviewing</button>
              <button className="btn btn-danger" disabled={saving} onClick={() => save("rejected")}>✕ Reject</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
