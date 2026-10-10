import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { setToken } from "../api";

/** Lands here from the backend's OAuth redirect: /oauth/callback?token=<JWT>.
 *  Stores the token, then reloads so the app re-boots as signed-in. */
export default function OAuthCallback() {
  const [params] = useSearchParams();
  const navigate = useNavigate();

  useEffect(() => {
    const token = params.get("token");
    const error = params.get("error");
    if (token) {
      setToken(token, true); // OAuth sign-ins persist the session
      window.location.replace("/app"); // full reload so the auth boot runs
      return;
    }
    navigate(`/login?oauth_error=${error || "invalid_response"}`, { replace: true });
  }, [params, navigate]);

  return (
    <div className="boot-screen">
      <div className="boot-logo">Resume<span>IQ</span></div>
      <div className="spinner" />
      <p className="dim small">Completing sign-in…</p>
    </div>
  );
}
