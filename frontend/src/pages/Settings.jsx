import { useEffect, useState } from "react";
import { DEFAULT_WEIGHTS, useApp } from "../store";
import { useToast } from "../components/Toast.jsx";

const LABELS = {
  skills: "Skills",
  experience: "Experience",
  projects: "Projects",
  education: "Education",
  certifications: "Certifications",
};

function rebalance(weights, changedKey, newValue) {
  const next = { ...weights, [changedKey]: newValue };
  const others = Object.keys(next).filter((k) => k !== changedKey);
  const remaining = 100 - newValue;
  const othersSum = others.reduce((s, k) => s + next[k], 0);
  if (othersSum <= 0) {
    others.forEach((k) => { next[k] = Math.round(remaining / others.length); });
  } else {
    others.forEach((k) => { next[k] = Math.max(0, Math.round((next[k] / othersSum) * remaining)); });
  }
  // Fix rounding drift on the last key.
  const drift = 100 - Object.values(next).reduce((s, x) => s + x, 0);
  if (drift !== 0) next[others[others.length - 1]] += drift;
  return next;
}

export default function Settings() {
  const { settings, saveSettings, theme, setTheme, user } = useApp();
  const toast = useToast();
  const [weights, setWeights] = useState(settings.weights);
  const [pii, setPii] = useState(settings.piiRedaction);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setWeights(settings.weights);
    setPii(settings.piiRedaction);
  }, [settings]);

  const total = Object.values(weights).reduce((s, x) => s + x, 0);

  const onSlide = (key, value) => setWeights((w) => rebalance(w, key, Number(value)));

  const persist = async () => {
    setSaving(true);
    try {
      await saveSettings({ weights, piiRedaction: pii, theme });
      toast("Settings saved", "Weights apply to the next match run.", "success");
    } catch (err) {
      toast("Could not save settings", err.message, "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="stack" style={{ maxWidth: 860 }}>
      <div className="card card-pad">
        <div className="card-title">
          <div>
            <h3>Scoring weights</h3>
            <p className="small dim">Slider values auto-balance to 100%. New weights apply on the next match run.</p>
          </div>
          <span className={`chip ${total === 100 ? "green" : "red"}`}>{total}%</span>
        </div>
        {Object.keys(LABELS).map((key) => (
          <div className="slider-row" key={key}>
            <span className="small dim" style={{ fontWeight: 600 }}>{LABELS[key]}</span>
            <input
              type="range"
              min="0"
              max="100"
              value={weights[key] ?? 0}
              onChange={(e) => onSlide(key, e.target.value)}
            />
            <span className="val mono">{weights[key] ?? 0}%</span>
          </div>
        ))}
        <div className="row" style={{ marginTop: 8 }}>
          <button className="btn btn-ghost btn-sm" onClick={() => setWeights({ ...DEFAULT_WEIGHTS })}>Reset to defaults</button>
        </div>
      </div>

      <div className="card card-pad">
        <h3>Privacy & fairness</h3>
        <div className="setting-line">
          <div>
            <b>PII redaction</b>
            <p className="small dim">Mask emails, phone numbers, addresses and government IDs in every uploaded resume. Applies to new uploads.</p>
          </div>
          <label className="switch">
            <input type="checkbox" checked={pii} onChange={(e) => setPii(e.target.checked)} />
            <span className="track-el" />
          </label>
        </div>
        <div className="setting-line">
          <div>
            <b>Bias-aware screening</b>
            <p className="small dim">
              Protected attributes (gender, age, religion, caste, marital status, nationality) are excluded from
              scoring by design, and every score ships a transparent criteria list. This is always on.
            </p>
          </div>
          <label className="switch">
            <input type="checkbox" checked disabled readOnly />
            <span className="track-el" />
          </label>
        </div>
        <div className="setting-line">
          <div>
            <b>Theme</b>
            <p className="small dim">Switch between light and dark mode. Saved per account.</p>
          </div>
          <div className="segmented">
            <button className={theme === "light" ? "on" : ""} onClick={() => setTheme("light")}>☀️ Light</button>
            <button className={theme === "dark" ? "on" : ""} onClick={() => setTheme("dark")}>🌙 Dark</button>
          </div>
        </div>
      </div>

      <div className="spread">
        <span className="small dim">Signed in as {user?.email}</span>
        <button className="btn btn-primary" onClick={persist} disabled={saving}>{saving ? "Saving…" : "Save settings"}</button>
      </div>
    </div>
  );
}
