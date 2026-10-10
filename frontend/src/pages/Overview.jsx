import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, formatRelative } from "../api";
import { useApp } from "../store";
import ScoreRing from "../components/ScoreRing.jsx";

export default function Overview() {
  const { user, activeJdId, setActiveJdId } = useApp();
  const navigate = useNavigate();
  const [jds, setJds] = useState([]);
  const [resumesCount, setResumesCount] = useState(0);
  const [results, setResults] = useState([]);
  const [activity, setActivity] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [jdList, resumeList] = await Promise.all([api.get("/api/jd"), api.get("/api/resumes")]);
        setJds(jdList);
        setResumesCount(resumeList.length);
        const target = jdList.find((j) => j.id === activeJdId) || jdList[0];
        if (target) {
          if (target.id !== activeJdId) setActiveJdId(target.id);
          setResults(await api.get(`/api/jd/${target.id}/results`));
        }
        setActivity(await api.get("/api/review/activity"));
      } finally {
        setLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const shortlisted = results.filter((r) => r.status === "shortlisted").length;
  const pending = results.filter((r) => r.status === "pending").length;
  const avg = results.length ? Math.round(results.reduce((s, r) => s + r.score, 0) / results.length) : 0;
  const jd = jds.find((j) => j.id === (activeJdId ?? jds[0]?.id));

  const stats = [
    { label: "Total Candidates", value: results.length || resumesCount, icon: "👥", bg: "var(--primary-soft)", color: "var(--primary)" },
    { label: "Avg. Match Score", value: `${avg}%`, icon: "🎯", bg: "var(--success-soft)", color: "var(--success)" },
    { label: "Shortlisted", value: shortlisted, icon: "⭐", bg: "var(--warn-soft)", color: "var(--warn)" },
    { label: "Pending Review", value: pending, icon: "🕓", bg: "var(--panel-2)", color: "var(--text-2)" },
  ];

  if (loading) return <div className="empty"><div className="spinner" style={{ margin: "0 auto" }} /></div>;

  const firstName = (user?.full_name || user?.email || "").split(/[\s@.]+/).filter(Boolean)[0] || "there";
  const hour = new Date().getHours();
  const daypart = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";

  return (
    <div className="stack">
      <div>
        <h2 style={{ margin: 0 }}>{daypart}, {firstName} 👋</h2>
        <p className="dim small">Here's where your screening stands today.</p>
      </div>
      <div className="spread">
        <div>
          <h2 style={{ margin: 0 }}>{jd ? jd.title : "No job description yet"}</h2>
          <p className="dim small">
            {jd ? `Active role · created ${formatRelative(jd.created_at)}` : "Create one in Upload & JD to start screening."}
          </p>
        </div>
        <div className="row">
          {jds.length > 0 && (
            <select className="control" value={activeJdId ?? jds[0].id} onChange={(e) => setActiveJdId(Number(e.target.value))}>
              {jds.map((j) => <option key={j.id} value={j.id}>{j.title}</option>)}
            </select>
          )}
          <Link to="/app/candidates"><button className="btn btn-primary btn-sm">Review candidates</button></Link>
        </div>
      </div>

      <div className="grid-4">
        {stats.map((s) => (
          <div className="card stat" key={s.label}>
            <div className="icon" style={{ background: s.bg, color: s.color }}>{s.icon}</div>
            <div>
              <div className="label">{s.label}</div>
              <div className="value">{s.value}</div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid-2">
        <div className="card card-pad">
          <div className="card-title">
            <h3>Top ranked candidates</h3>
            <Link to="/app/candidates" className="small">View all →</Link>
          </div>
          {results.length === 0 ? (
            <div className="empty">
              <div className="big">🗂️</div>
              <p>No ranked candidates yet.</p>
              <button className="btn btn-primary btn-sm" style={{ marginTop: 12 }} onClick={() => navigate("/app/upload")}>
                Upload resumes & run a match
              </button>
            </div>
          ) : (
            <div className="feed">
              {results.slice(0, 5).map((r) => (
                <div className="feed-item" key={r.result_id} style={{ cursor: "pointer" }} onClick={() => navigate("/app/candidates")}>
                  <ScoreRing score={r.score} size={44} stroke={4} />
                  <div className="what">
                    <b>{r.candidate_name}</b>
                    <div className="small dim">#{r.rank} · {r.skills.slice(0, 4).join(", ") || "no detected skills"}</div>
                  </div>
                  <span className={`badge ${r.status}`}>{r.status}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card card-pad">
          <div className="card-title"><h3>Recent activity</h3></div>
          {activity.length === 0 ? (
            <div className="empty">
              <div className="big">📋</div>
              <p>Recruiter decisions will appear here as you review candidates.</p>
            </div>
          ) : (
            <div className="feed">
              {activity.map((a, i) => (
                <div className="feed-item" key={i}>
                  <span className="dot" style={{ background: a.status === "shortlisted" ? "var(--success)" : a.status === "rejected" ? "var(--danger)" : "var(--warn)" }} />
                  <div className="what">
                    <b>{a.candidate}</b>
                    <div className="small dim">
                      {a.status} · {a.jd_title} · AI score {a.ai_score}
                      {a.feedback ? ` · feedback: ${a.feedback.replace(/_/g, " ")}` : ""}
                    </div>
                  </div>
                  <time>{formatRelative(a.at)}</time>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
