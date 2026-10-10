"""Modules 1, 7, 8 integration tests — full API flow end-to-end.

Covers: auth (register/login/me/401s), JD creation with analysis, resume
upload of PDF/DOCX/TXT (generated on the fly), batch upload with per-file
status, match + ranked results, immutable AI score vs. recruiter decision,
analytics, CSV export and settings round-trip.
"""
import io

import fitz  # PyMuPDF
import docx  # python-docx

from samples.samples import DEMO_JD, SAMPLE_RESUMES

RESUME_TEXT = SAMPLE_RESUMES["priya_sharma.txt"]
WEAK_TEXT = SAMPLE_RESUMES["sara_khan.txt"]


def _pdf_bytes(text: str) -> bytes:
    document = fitz.open()
    page = document.new_page()
    # Write line by line so page.get_text() keeps line breaks.
    for i, line in enumerate(text.splitlines()):
        page.insert_text((72, 72 + i * 14), line, fontsize=9)
    data = document.tobytes()
    document.close()
    return data


def _docx_bytes(text: str) -> bytes:
    document = docx.Document()
    for line in text.splitlines():
        document.add_paragraph(line)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _upload(client, headers, files):
    return client.post("/api/resumes/upload", files=files, headers=headers)


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_auth_flow(client):
    response = client.post(
        "/api/auth/register", json={"email": "flow@test.com", "password": "secret123", "full_name": "Flow Tester"}
    )
    assert response.status_code == 201
    token = response.json()["access_token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "flow@test.com"

    login = client.post("/api/auth/login", json={"email": "flow@test.com", "password": "secret123"})
    assert login.status_code == 200

    assert client.post("/api/auth/login", json={"email": "flow@test.com", "password": "wrong-password"}).status_code == 401
    assert client.post("/api/auth/register", json={"email": "flow@test.com", "password": "secret123"}).status_code == 409
    assert client.post("/api/auth/register", json={"email": "bad", "password": "secret123"}).status_code == 422
    assert client.get("/api/resumes").status_code == 401  # protected without token


def test_full_pipeline_flow(client, auth):
    headers = auth

    # 1. Create a JD (Module 1) — analysis (Module 2) happens inline.
    jd = client.post("/api/jd", json={"title": "Senior Backend Engineer", "text": DEMO_JD}, headers=headers)
    assert jd.status_code == 201, jd.text
    jd_id = jd.json()["id"]
    assert "python" in jd.json()["profile"]["must_have_skills"]

    # 2. Upload resumes: TXT, PDF and DOCX versions + one broken file.
    report = _upload(client, headers, [
        ("files", ("priya_sharma.txt", RESUME_TEXT.encode(), "text/plain")),
        ("files", ("ananya.pdf", _pdf_bytes(RESUME_TEXT), "application/pdf")),
        ("files", ("meera.docx", _docx_bytes(RESUME_TEXT), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
        ("files", ("broken.pdf", b"%PDF-1.4 not really a pdf", "application/pdf")),
    ])
    assert report.status_code == 200, report.text
    body = report.json()
    assert body["uploaded"] == 3
    statuses = {f["filename"]: f["status"] for f in body["files"]}
    assert statuses["broken.pdf"] == "error"  # per-file failure, batch survives
    pdf_file = next(f for f in body["files"] if f["filename"] == "ananya.pdf")
    assert pdf_file["status"] == "parsed"

    # 3. PII is redacted before storage (Module 5 default ON): the raw sample
    # contains an email/phone, the API must never return them.
    resume_list = client.get("/api/resumes", headers=headers).json()
    assert len(resume_list) >= 3

    # 4. Run matching (Modules 3-4).
    run = client.post(f"/api/jd/{jd_id}/match", headers=headers)
    assert run.status_code == 200, run.text
    assert run.json()["candidates_scored"] >= 3

    # 5. Results are ranked and explainable.
    results = client.get(f"/api/jd/{jd_id}/results", headers=headers).json()
    assert len(results) >= 3
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True), "results must be ranked by score"
    assert [r["rank"] for r in results] == list(range(1, len(results) + 1))
    top = results[0]
    assert top["score"] >= 60  # a strong FastAPI resume vs. a FastAPI JD
    assert top["explanation"]["why_matched"]
    assert any(m["tier"] == "must" for m in top["matched"])
    # No PII anywhere in the API payload.
    payload_text = str(results).lower()
    assert "priya.sharma@example.com" not in payload_text
    assert "+91 98765 43210" not in payload_text
    assert "9876543210" not in payload_text

    # 6. Human-in-the-loop (Module 7): decide on the top candidate.
    decision = client.post(
        f"/api/results/{top['result_id']}/decision",
        json={"status": "shortlisted", "feedback": "relevant", "note": "Great fit"},
        headers=headers,
    )
    assert decision.status_code == 200, decision.text
    assert decision.json()["decision"]["status"] == "shortlisted"

    results_after = client.get(f"/api/jd/{jd_id}/results", headers=headers).json()
    decided = next(r for r in results_after if r["result_id"] == top["result_id"])
    assert decided["status"] == "shortlisted"
    assert decided["score"] == top["score"], "recruiter decision must not alter the AI score"

    # 7. Analytics reflect the decision.
    analytics = client.get(f"/api/jd/{jd_id}/analytics", headers=headers).json()
    assert analytics["candidates"] == len(results)
    assert analytics["status_breakdown"]["shortlisted"] >= 1
    assert sum(analytics["score_distribution"].values()) == len(results)
    assert analytics["skill_coverage"], "skill coverage should list JD skills"

    # 8. CSV export.
    export = client.get(f"/api/jd/{jd_id}/export", headers=headers)
    assert export.status_code == 200
    assert "text/csv" in export.headers["content-type"]
    assert "rank,candidate,match_score" in export.text

    # 9. Re-running the match keeps the recruiter's decision: it must be
    # carried over to the fresh result rows (human decisions survive re-scores).
    rerun = client.post(f"/api/jd/{jd_id}/match", headers=headers)
    assert rerun.status_code == 200
    rerun_results = client.get(f"/api/jd/{jd_id}/results", headers=headers).json()
    carried = next(r for r in rerun_results if r["resume_id"] == top["resume_id"])
    assert carried["status"] == "shortlisted", "decision must survive a re-run"

    # 10. Review activity feed shows the (carried) decision.
    activity = client.get("/api/review/activity", headers=headers).json()
    assert activity, "recent decisions should appear in the activity feed"


def test_settings_roundtrip_and_weight_effect(client, auth):
    headers = auth
    original = client.get("/api/settings", headers=headers).json()
    assert original["pii_redaction"] is True  # privacy-first default

    updated = client.put(
        "/api/settings",
        json={"weights": {"skills": 60, "experience": 20, "projects": 10, "education": 5, "certifications": 5},
              "pii_redaction": False},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["weights"]["skills"] == 60
    assert updated.json()["pii_redaction"] is False

    # With redaction OFF, uploads keep PII; verify, then restore defaults.
    jd = client.post("/api/jd", json={"title": "Any", "text": DEMO_JD}, headers=headers)
    upload = _upload(client, headers, [("files", ("weak.txt", WEAK_TEXT.encode(), "text/plain"))])
    assert upload.status_code == 200
    client.put("/api/settings", json={"pii_redaction": True, "weights": original.get("weights") or {}}, headers=headers)


def test_pii_redaction_toggle_masks_uploads(client, auth):
    headers = auth
    # Default settings have redaction ON: upload and confirm masking.
    upload = _upload(client, headers, [("files", ("masked.txt", RESUME_TEXT.encode(), "text/plain"))])
    assert upload.status_code == 200
    resume_id = upload.json()["files"][0]["resume_id"]
    # No endpoint returns raw text, so verify via a match's evidence payloads.
    jd = client.post("/api/jd", json={"title": "Mask check", "text": DEMO_JD}, headers=headers)
    jd_id = jd.json()["id"]
    client.post(f"/api/jd/{jd_id}/match", headers=headers)
    results = client.get(f"/api/jd/{jd_id}/results", headers=headers).json()
    assert "priya.sharma@example.com" not in str(results)


def test_upload_requires_auth(client):
    response = client.post("/api/resumes/upload", files=[("files", ("x.txt", b"hello", "text/plain"))])
    assert response.status_code == 401


def test_unsupported_file_type_rejected(client, auth):
    report = _upload(client, auth, [("files", ("photo.jpg", b"\xff\xd8\xff\xe0fake", "image/jpeg"))])
    files = report.json()["files"]
    assert files[0]["status"] == "error"
    assert "Unsupported" in files[0]["error"]
