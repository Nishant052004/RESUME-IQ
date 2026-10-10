import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, formatRelative } from "../api";
import { useApp } from "../store";
import { useToast } from "../components/Toast.jsx";

export default function Upload() {
  const { activeJdId, setActiveJdId, settings } = useApp();
  const toast = useToast();
  const navigate = useNavigate();
  const fileInputRef = useRef(null);

  const [jds, setJds] = useState([]);
  const [title, setTitle] = useState("");
  const [jdText, setJdText] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzed, setAnalyzed] = useState(null);
  const [files, setFiles] = useState([]); // {name, status, detail}
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const jdList = await api.get("/api/jd");
        setJds(jdList);
        // Surface the active JD's detected requirements right away.
        const target = jdList.find((j) => j.id === (activeJdId ?? jdList[0]?.id));
        if (target && !analyzed) setAnalyzed(target.profile);
      } catch { /* list stays empty */ }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const currentJd = jds.find((j) => j.id === (activeJdId ?? jds[0]?.id));

  const pickJd = async (jd) => {
    setActiveJdId(jd.id);
    setAnalyzed(jd.profile);
    setTitle(jd.title);
    setJdText("");
    try {
      const fresh = await api.get(`/api/jd/${jd.id}`);
      setAnalyzed(fresh.profile);
    } catch { /* keep profile from list */ }
  };

  const analyzeJd = async () => {
    if (jdText.trim().length < 30) {
      toast("Job description too short", "Paste at least a couple of sentences.", "error");
      return;
    }
    setAnalyzing(true);
    try {
      const created = await api.post("/api/jd", { title, text: jdText });
      setAnalyzed(created.profile);
      setTitle(created.title);
      setActiveJdId(created.id);
      setJds((list) => [created, ...list]);
      toast("JD analyzed", `Detected ${created.profile.must_have_skills.length} required + ${created.profile.nice_to_have_skills.length} nice-to-have skills.`, "success");
    } catch (err) {
      toast("Analysis failed", err.message, "error");
    } finally {
      setAnalyzing(false);
    }
  };

  const handleFiles = async (fileList) => {
    if (!fileList || fileList.length === 0) return;
    const accepted = [...fileList].filter((f) => /\.(pdf|docx|txt|md)$/i.test(f.name));
    const rejected = [...fileList].filter((f) => !/\.(pdf|docx|txt|md)$/i.test(f.name));
    if (rejected.length) toast("Some files were skipped", "Only PDF, DOCX and TXT resumes are supported.", "error");
    if (!accepted.length) return;

    const pendingRows = accepted.map((f) => ({ name: f.name, status: "uploading", detail: "" }));
    setFiles((rows) => [...pendingRows, ...rows]);
    setUploading(true);

    const formData = new FormData();
    accepted.forEach((f) => formData.append("files", f));
    try {
      const report = await api.upload("/api/resumes/upload", formData);
      setFiles((rows) =>
        rows.map((row) => {
          const match = report.files.find((f) => f.filename === row.name);
          if (!match) return row;
          return match.status === "parsed"
            ? { name: row.name, status: "parsed", detail: `${match.candidate_name} · ${match.skills_found} skills · ${match.experience_years} yr(s)` }
            : { name: row.name, status: "error", detail: match.error };
        }),
      );
      toast(`${report.uploaded} resume(s) parsed`, report.uploaded ? "Ready to run a match in Candidates." : "", report.uploaded ? "success" : "error");
    } catch (err) {
      setFiles((rows) => rows.map((r) => (pendingRows.some((p) => p.name === r.name) ? { ...r, status: "error", detail: err.message } : r)));
      toast("Upload failed", err.message, "error");
    } finally {
      setUploading(false);
    }
  };

  const mustSkills = analyzed?.must_have_skills || [];
  const niceSkills = analyzed?.nice_to_have_skills || [];

  return (
    <div className="stack">
      <div className="grid-2">
        <div className="card card-pad">
          <div className="card-title">
            <h3>1 · Job description</h3>
            {jds.length > 0 && (
              <select className="control" value={activeJdId ?? ""} onChange={(e) => pickJd(jds.find((j) => j.id === Number(e.target.value)))}>
                <option value="" disabled>Past JDs…</option>
                {jds.map((j) => <option key={j.id} value={j.id}>{j.title}</option>)}
              </select>
            )}
          </div>
          <div className="field">
            <label>Role title (optional)</label>
            <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Senior Backend Engineer" />
          </div>
          <div className="field">
            <label>Paste the full job description</label>
            <textarea
              rows={9}
              value={jdText}
              onChange={(e) => setJdText(e.target.value)}
              placeholder="Paste responsibilities, requirements, skills, experience…"
            />
          </div>
          <button className="btn btn-primary" onClick={analyzeJd} disabled={analyzing}>
            {analyzing ? "Analyzing…" : "✨ Analyze JD"}
          </button>
          {currentJd && (
            <p className="small dim" style={{ marginTop: 10 }}>
              Active role: <b>{currentJd.title}</b> · created {formatRelative(currentJd.created_at)}
            </p>
          )}
        </div>

        <div className="card card-pad">
          <h3>Detected requirements</h3>
          {!analyzed ? (
            <div className="empty">
              <div className="big">🧠</div>
              <p>Analyze a JD to extract skills, experience and education requirements.</p>
            </div>
          ) : (
            <div className="stack" style={{ gap: 12 }}>
              <div>
                <div className="small dim" style={{ marginBottom: 6 }}>Must-have skills</div>
                <div className="jd-chip-list">
                  {mustSkills.length ? mustSkills.map((s) => <span className="chip" key={s}>{s}</span>) : <span className="small dim">none detected</span>}
                </div>
              </div>
              {niceSkills.length > 0 && (
                <div>
                  <div className="small dim" style={{ marginBottom: 6 }}>Nice to have</div>
                  <div className="jd-chip-list">{niceSkills.map((s) => <span className="chip amber" key={s}>{s}</span>)}</div>
                </div>
              )}
              <div className="small dim">
                Minimum experience: <b style={{ color: "var(--text)" }}>{analyzed.min_years_experience || "—"} year(s)</b>
                {analyzed.education?.length > 0 && <> · Education: <b style={{ color: "var(--text)" }}>{analyzed.education.join(", ")}</b></>}
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="card card-pad">
        <div className="card-title">
          <h3>2 · Upload resumes</h3>
          <span className="chip gray">PDF · DOCX · TXT</span>
        </div>
        <div
          className={`dropzone ${dragOver ? "over" : ""}`}
          onClick={() => fileInputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => { e.preventDefault(); setDragOver(false); handleFiles(e.dataTransfer.files); }}
        >
          <div className="big">📄</div>
          <p><b>Drag & drop resumes here</b> or click to browse</p>
          <p className="small dim">Batch upload supported — one file failing never blocks the rest. PII redaction is {settings.piiRedaction ? "ON" : "OFF"}.</p>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.docx,.txt,.md"
            style={{ display: "none" }}
            onChange={(e) => { handleFiles(e.target.files); e.target.value = ""; }}
          />
        </div>

        {files.length > 0 && (
          <div className="stack" style={{ gap: 8, marginTop: 14 }}>
            {files.map((f) => (
              <div className="file-row" key={f.name}>
                <div className="row" style={{ minWidth: 0 }}>
                  <span>{f.status === "parsed" ? "✅" : f.status === "error" ? "❌" : <span className="spinner" style={{ width: 14, height: 14 }} />}</span>
                  <div style={{ minWidth: 0 }}>
                    <b className="small" style={{ display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{f.name}</b>
                    <span className="small dim">{f.detail || (f.status === "uploading" ? "Parsing…" : "")}</span>
                  </div>
                </div>
                <span className={`chip ${f.status === "parsed" ? "green" : f.status === "error" ? "red" : "gray"}`}>
                  {f.status === "parsed" ? "parsed" : f.status === "error" ? "failed" : "uploading"}
                </span>
              </div>
            ))}
          </div>
        )}

        <div className="spread" style={{ marginTop: 16 }}>
          <span className="small dim">Parsed resumes are stored redacted and bias-screened.</span>
          <button className="btn btn-primary" onClick={() => navigate("/app/candidates")} disabled={uploading}>
            Go to candidates →
          </button>
        </div>
      </div>
    </div>
  );
}
