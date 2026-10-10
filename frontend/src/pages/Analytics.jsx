import { useEffect, useRef, useState } from "react";
import { Chart } from "chart.js/auto";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useApp } from "../store";

const CSS = getComputedStyle(document.documentElement);
const v = (name) => CSS.getPropertyValue(name).trim() || undefined;

export default function Analytics() {
  const { activeJdId } = useApp();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const coverageRef = useRef(null);
  const statusRef = useRef(null);
  const distRef = useRef(null);
  const chartsRef = useRef([]);

  useEffect(() => {
    if (!activeJdId) {
      setLoading(false);
      return;
    }
    api.get(`/api/jd/${activeJdId}/analytics`)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [activeJdId]);

  useEffect(() => {
    if (!data) return;
    chartsRef.current.forEach((c) => c?.destroy());

    const coverage = data.skill_coverage || [];
    chartsRef.current = [
      new Chart(coverageRef.current, {
        type: "bar",
        data: {
          labels: coverage.map((s) => s.skill),
          datasets: [{
            label: "Candidates with skill",
            data: coverage.map((s) => (s.total ? Math.round((s.covered / s.total) * 100) : 0)),
            backgroundColor: v("--primary"),
            borderRadius: 6,
          }],
        },
        options: {
          indexAxis: "y",
          plugins: { legend: { display: false }, tooltip: { callbacks: { label: (ctx) => `${ctx.parsed.x}% of candidates` } } },
          scales: {
            x: { max: 100, ticks: { callback: (x) => `${x}%` }, grid: { color: v("--border") } },
            y: { grid: { display: false }, ticks: { color: v("--text-2") } },
          },
        },
      }),
      new Chart(statusRef.current, {
        type: "doughnut",
        data: {
          labels: ["Shortlisted", "Pending", "Rejected"],
          datasets: [{
            data: [data.status_breakdown.shortlisted, data.status_breakdown.pending, data.status_breakdown.rejected],
            backgroundColor: [v("--success"), v("--warn"), v("--danger")],
            borderWidth: 0,
          }],
        },
        options: {
          cutout: "62%",
          plugins: { legend: { position: "bottom", labels: { color: v("--text-2"), usePointStyle: true } } },
        },
      }),
      new Chart(distRef.current, {
        type: "bar",
        data: {
          labels: Object.keys(data.score_distribution),
          datasets: [{
            label: "Candidates",
            data: Object.values(data.score_distribution),
            backgroundColor: [v("--danger"), v("--warn"), v("--primary"), v("--primary-2"), v("--success")],
            borderRadius: 6,
          }],
        },
        options: {
          plugins: { legend: { display: false } },
          scales: {
            x: { grid: { display: false }, ticks: { color: v("--text-2") } },
            y: { beginAtZero: true, ticks: { precision: 0, color: v("--text-2") }, grid: { color: v("--border") } },
          },
        },
      }),
    ];
    return () => chartsRef.current.forEach((c) => c?.destroy());
  }, [data]);

  if (loading) return <div className="empty"><div className="spinner" style={{ margin: "0 auto" }} /></div>;

  if (!data) {
    return (
      <div className="card empty">
        <div className="big">📊</div>
        <h3>No analytics yet</h3>
        <p className="dim">Select a job description and run a match first.</p>
        <Link to="/app/candidates"><button className="btn btn-primary" style={{ marginTop: 12 }}>Go to Candidates</button></Link>
      </div>
    );
  }

  return (
    <div className="stack">
      <div className="grid-2" style={{ gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>
        <div className="card stat"><div className="icon" style={{ background: "var(--primary-soft)", color: "var(--primary)" }}>👥</div><div><div className="label">Candidates scored</div><div className="value">{data.candidates}</div></div></div>
        <div className="card stat"><div className="icon" style={{ background: "var(--success-soft)", color: "var(--success)" }}>🎯</div><div><div className="label">Average score</div><div className="value">{data.avg_score}%</div></div></div>
        <div className="card stat"><div className="icon" style={{ background: "var(--warn-soft)", color: "var(--warn)" }}>⭐</div><div><div className="label">Shortlisted</div><div className="value">{data.status_breakdown.shortlisted}</div></div></div>
      </div>

      <div className="grid-2">
        <div className="card card-pad">
          <h3>Skill coverage</h3>
          <p className="small dim" style={{ marginBottom: 12 }}>Share of scored candidates that have each JD skill.</p>
          {data.skill_coverage.length === 0
            ? <div className="empty"><p className="dim">Run a match to populate skill coverage.</p></div>
            : <canvas ref={coverageRef} height={280} />}
        </div>
        <div className="card card-pad">
          <h3>Review status breakdown</h3>
          <p className="small dim" style={{ marginBottom: 12 }}>Recruiter decisions across all scored candidates.</p>
          {data.candidates === 0
            ? <div className="empty"><p className="dim">No candidates scored yet.</p></div>
            : <canvas ref={statusRef} height={280} />}
        </div>
      </div>

      <div className="card card-pad">
        <h3>Match score distribution</h3>
        <p className="small dim" style={{ marginBottom: 12 }}>How the weighted scores spread across the candidate pool.</p>
        {data.candidates === 0
          ? <div className="empty"><p className="dim">No candidates scored yet.</p></div>
          : <canvas ref={distRef} height={90} />}
      </div>
    </div>
  );
}
