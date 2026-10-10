import { useEffect, useState } from "react";
import { useToast } from "./Toast.jsx";

/** Guided setup for a not-yet-configured OAuth provider. Shows the exact
 *  callback URL to register, links to the provider console, and where to
 *  paste the resulting credentials. */
export default function OAuthSetupModal({ provider, onClose }) {
  const toast = useToast();
  const [copied, setCopied] = useState(false);

  const isGithub = provider === "github";
  const name = isGithub ? "GitHub" : "Google";
  const consoleUrl = isGithub
    ? "https://github.com/settings/applications/new"
    : "https://console.cloud.google.com/apis/credentials";
  const callbackUrl = `${window.location.origin}/api/auth/oauth/${provider}/callback`;
  const envKeys = isGithub ? ["GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET"] : ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"];

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(callbackUrl);
    } catch {
      const el = document.createElement("textarea");
      el.value = callbackUrl;
      document.body.appendChild(el);
      el.select();
      document.execCommand("copy");
      el.remove();
    }
    setCopied(true);
    toast("Copied", "Callback URL is on your clipboard.", "success");
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" style={{ maxWidth: 560 }} role="dialog" aria-modal="true">
        <div className="modal-head">
          <h2>Set up {name} sign-in</h2>
          <button className="close-x" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <div className="modal-body">
          <p className="dim small">
            {name} sign-in needs a one-time app registration in your {name} account — about two minutes.
            Until then, the button stays inactive on this server.
          </p>

          <div className="setup-step">
            <div className="setup-num">1</div>
            <div>
              Open the {isGithub ? "OAuth app registration" : "credentials console"}:
              <div>
                <a href={consoleUrl} target="_blank" rel="noreferrer" className="setup-link">
                  {consoleUrl.replace("https://", "")} ↗
                </a>
              </div>
            </div>
          </div>

          <div className="setup-step">
            <div className="setup-num">2</div>
            <div style={{ width: "100%" }}>
              {isGithub ? (
                <>
                  Fill the form — any app name works, e.g. <b>ResumeIQ</b>. Homepage URL: <b>{window.location.origin}</b>.
                  For the <b>Authorization callback URL</b>, paste exactly:
                </>
              ) : (
                <>
                  Create an <b>OAuth client ID</b> (Web application), then under Authorized redirect URIs paste exactly:
                </>
              )}
              <div className="setup-copy">
                <code>{callbackUrl}</code>
                <button className="btn btn-sm" onClick={copy}>{copied ? "✓ Copied" : "Copy"}</button>
              </div>
            </div>
          </div>

          <div className="setup-step">
            <div className="setup-num">3</div>
            <div>
              {isGithub
                ? "Copy the Client ID and press “Generate a new client secret”."
                : "Copy the Client ID and Client Secret shown after creation."}
            </div>
          </div>

          <div className="setup-step">
            <div className="setup-num">4</div>
            <div style={{ width: "100%" }}>
              Paste them into <code>backend/.env</code> (already scaffolded for you):
              <pre className="setup-env">{envKeys[0]}=your-client-id{"\n"}{envKeys[1]}=your-client-secret</pre>
              then restart the backend. The button goes live automatically — the “setup” chip disappears.
            </div>
          </div>

          <p className="small dim" style={{ marginBottom: 0 }}>
            Tip: register the same callback path against your public domain when you deploy —
            multiple callback URLs are supported by both providers.
          </p>
        </div>
      </div>
    </div>
  );
}
