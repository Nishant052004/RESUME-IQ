import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useApp } from "../store";
import { useToast } from "../components/Toast.jsx";
import ScoreRing from "../components/ScoreRing.jsx";
import CandidateModal from "../components/CandidateModal.jsx";

const FILTERS = ["all", "shortlisted", "pending", "rejected"];
const SORTS = {
  score: { label: "Match score", fn: (a, b) => b.score - a.score },
  name: { label: "Name (A–Z)", fn: (a, b) => a.candidate_name.localeCompare(b.candidate_name) },
  experience: { label: "Experience", fn: (a, b) => b.experience_years - a.experience_years },
};

export default function Candidates() {
  const { activeJdId } = useApp();
  const toast = useToast();
  const [results, setResults] = useState([]);
  const [jd, setJd] = useState(null);
  const [filter, setFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState("score");
  const [selected, setSelected] = useState(null);
  const [matching, setMatching] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!activeJdId) {
      setLoading(false);
      return;
    }
    try {
      const [resultsData, jds] = await Promise.all([
        api.get(`/api/jd/${activeJdId}/results`).catch(() => []),
        api.get("/api/jd"),
      ]);
      setResults(resultsData);
      setJd(jds.find((j) => j.id === activeJdId) || null);
    } finally {
      setLoading(false);
    }
  }, [activeJdId]);

  useEffect(() => {
    setLoading(true);
    load();
  }, [load]);

  const runMatch = async () => {
    setMatching(true);
    try {
      const run = await api.post(`/api/jd/${activeJdId}/match`);
      toast("Match complete", `${run.candidates_scored} candidate(s) scored · top score ${run.top_score}%.`, "success");
      await load();
    } catch (err) {
      toast("Match failed", err.message, "error");
    } finally {
      setMatching(false);
    }
  };

  const visible = useMemo(() => {
    let list = results;
    if (filter !== "all") list = list.filter((r) => r.status === filter);
    if (query.trim()) {
      const q = query.trim().toLowerCase();
      list = list.filter(
        (r) => r.candidate_name.toLowerCase().includes(q) || r.skills.some((s) => s.includes(q)),
      );
    }
    return [...list].sort(SORTS[sort].fn);
  }, [results, filter, query, sort]);

  const counts = useMemo(() => {
    const base = { all: results.length, shortlisted: 0, pending: 0, rejected: 0 };
    results.forEach((r) => { if (r.status in base && r.status !== "all") base[r.status] += 1; });
    return base;
  }, [results]);

  if (loading) return <div className="empty"><div className="spinner" style={{ margin: "0 auto" }} /></div>;

  if (!activeJdId) {
    return (
      <div className="card empty">
        <div className="big">📝</div>
        <h3>No job description selected</h3>
        <p className="dim">Create and analyze a job description first.</p>
        <Link to="/app/upload"><button className="btn btn-primary" style={{ marginTop: 14 }}>Go to Upload & JD</button></Link>
      </div>
    );
  }

  return (
    <div className="stack">
      <div className="spread" style={{ flexWrap: "wrap" }}>
        <div>
          <h2 style={{ margin: 0 }}>{jd?.title || "Candidates"}</h2>
          <p className="dim small">
            {results.length
              ? `${results.length} candidate(s) ranked against this role`
              : "Run a match to rank uploaded resumes against this JD."}
          </p>
        </div>
        <div className="row">
          {results.length > 0 && (
            <a href={`/api/jd/${activeJdId}/export`} download>
              <button className="btn btn-ghost btn-sm">⬇ Export CSV</button>
            </a>
          )}
          <button className="btn btn-primary" onClick={runMatch} disabled={matching}>
            {matching ? "Scoring…" : results.length ? "↻ Re-run match" : "▶ Run match"}
          </button>
        </div>
      </div>

      <div className="filters">
        <div className="segmented">
          {FILTERS.map((f) => (
            <button key={f} className={filter === f ? "on" : ""} onClick={() => setFilter(f)}>
              {f[0].toUpperCase() + f.slice(1)} ({counts[f] ?? 0})
            </button>
          ))}
        </div>
        <input className="search-input" placeholder="Search name or skill…" value={query} onChange={(e) => setQuery(e.target.value)} />
        <select className="control" value={sort} onChange={(e) => setSort(e.target.value)}>
          {Object.entries(SORTS).map(([key, s]) => <option key={key} value={key}>Sort: {s.label}</option>)}
        </select>
      </div>

      {visible.length === 0 ? (
        <div className="card empty">
          <div className="big">🔍</div>
          <h3>{results.length === 0 ? "No results yet" : "No candidates match your filters"}</h3>
          <p className="dim">
            {results.length === 0
              ? "Upload resumes, then run a match against the active job description."
              : "Try a different search or status filter."}
          </p>
          {results.length === 0 && <Link to="/app/upload"><button className="btn btn-primary" style={{ marginTop: 12 }}>Upload resumes</button></Link>}
        </div>
      ) : (
        <div className="stack" style={{ gap: 10 }}>
          {visible.map((r) => (
            <div className="card candidate-row" key={r.result_id} onClick={() => setSelected(r)}>
              <ScoreRing score={r.score} />
              <div style={{ minWidth: 0 }}>
                <div className="name">
                  <b>{r.candidate_name}</b>
                  <span className="small dim" style={{ marginLeft: 8 }}>#{r.rank}</span>
                </div>
                <div className="sub">
                  {r.experience_years} yr(s) · {r.matched.filter((m) => m.tier === "must").length} required skills matched
                  {r.missing.some((m) => m.tier === "must") && ` · missing ${r.missing.filter((m) => m.tier === "must").map((m) => m.skill).slice(0, 2).join(", ")}${r.missing.filter((m) => m.tier === "must").length > 2 ? "…" : ""}`}
                </div>
                <div className="meta">
                  {r.skills.slice(0, 6).map((s) => <span className="chip gray" key={s}>{s}</span>)}
                  {r.skills.length > 6 && <span className="chip gray">+{r.skills.length - 6}</span>}
                </div>
              </div>
              <span className={`badge ${r.status}`}>{r.status}</span>
              <button className="btn btn-ghost btn-sm" onClick={(e) => { e.stopPropagation(); setSelected(r); }}>
                Review →
              </button>
            </div>
          ))}
        </div>
      )}

      {selected && (
        <CandidateModal
          candidate={results.find((r) => r.result_id === selected.result_id) || selected}
          onClose={() => setSelected(null)}
          onDecision={load}
        />
      )}
    </div>
  );
}
