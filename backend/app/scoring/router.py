"""Scoring & results API (Modules 3-4) + analytics, export, settings."""
import csv
import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth.deps import get_current_user, get_user_settings
from ..database import get_db
from ..matching.engine import analyze_match
from ..models import Decision, JobDescription, MatchResult, Resume, User, UserSettings
from ..scoring.engine import score_resume

router = APIRouter(prefix="/api", tags=["scoring"])


def _get_jd(jd_id: int, user: User, db: Session) -> JobDescription:
    jd = db.get(JobDescription, jd_id)
    if jd is None or jd.user_id != user.id:
        raise HTTPException(status_code=404, detail="Job description not found.")
    return jd


@router.post("/jd/{jd_id}/match")
def run_matching(
    jd_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Run the full pipeline (extract → match → score → rank) for every resume
    of this user against one JD. Re-runs replace previous results; AI scores
    are only ever written here, never by recruiter decisions."""
    jd = _get_jd(jd_id, user, db)
    settings_row = get_user_settings(user, db)
    resumes = db.query(Resume).filter(Resume.user_id == user.id).all()
    if not resumes:
        raise HTTPException(status_code=400, detail="Upload at least one resume before running a match.")

    scored: list[tuple[int, dict]] = []
    for resume in resumes:
        match = analyze_match(resume.raw_text, resume.profile or {}, jd.raw_text, jd.profile or {})
        result = score_resume(resume.profile or {}, match, jd.profile or {}, settings_row.weights)
        scored.append((resume.id, result))

    scored.sort(key=lambda pair: pair[1]["score"], reverse=True)
    # Re-running a match replaces the result rows. Recruiter decisions are
    # preserved by re-attaching them (per resume) to the new result rows, so a
    # re-score never wipes human decisions.
    old_rows = db.query(MatchResult.id, MatchResult.resume_id).filter(MatchResult.jd_id == jd.id).all()
    carried: dict[int, tuple[str, str, str]] = {}
    if old_rows:
        old_resume_by_result = {row.id: row.resume_id for row in old_rows}
        for decision in db.query(Decision).filter(Decision.result_id.in_([r.id for r in old_rows])):
            resume_id = old_resume_by_result.get(decision.result_id)
            if resume_id is not None:
                carried[resume_id] = (decision.status, decision.feedback, decision.note)
        db.query(Decision).filter(Decision.result_id.in_([r.id for r in old_rows])).delete(synchronize_session=False)
    db.query(MatchResult).filter(MatchResult.jd_id == jd.id).delete(synchronize_session=False)

    new_result_by_resume: dict[int, int] = {}
    for rank, (resume_id, result) in enumerate(scored, start=1):
        row = MatchResult(
            jd_id=jd.id,
            resume_id=resume_id,
            score=result["score"],
            subscores=result["subscores"],
            rank=rank,
            matched=result["matched"],
            missing=result["missing"],
            explanation=result["explanation"],
            weights_used=result["active_weights"],
        )
        db.add(row)
        db.flush()
        new_result_by_resume[resume_id] = row.id

    for resume_id, (status, feedback, note) in carried.items():
        if resume_id in new_result_by_resume:
            db.add(Decision(
                result_id=new_result_by_resume[resume_id],
                user_id=user.id,
                status=status,
                feedback=feedback,
                note=note,
            ))
    db.commit()
    return {"jd_id": jd.id, "candidates_scored": len(scored), "top_score": scored[0][1]["score"] if scored else 0}


def _candidate_out(db: Session, result: MatchResult, resume: Resume) -> dict:
    profile = resume.profile or {}
    decision = db.query(Decision).filter(Decision.result_id == result.id).first()
    technical = (profile.get("skills", {}) or {}).get("technical", [])
    return {
        "result_id": result.id,
        "resume_id": resume.id,
        "candidate_name": profile.get("name") or resume.filename.rsplit(".", 1)[0],
        "filename": resume.filename,
        "rank": result.rank,
        "score": result.score,
        "subscores": result.subscores,
        "skills": technical[:12],
        "certifications": profile.get("certifications", []),
        "experience_years": (profile.get("experience", {}) or {}).get("total_years", 0),
        "education": profile.get("education", []),
        "projects": [
            {"title": p.get("title", "")} for p in profile.get("projects", [])[:5]
        ],
        "matched": result.matched,
        "missing": result.missing,
        "explanation": result.explanation,
        "weights_used": result.weights_used,
        "status": decision.status if decision else "pending",
        "recruiter_feedback": decision.feedback if decision else "",
        "recruiter_note": decision.note if decision else "",
        "decision_updated_at": decision.updated_at.isoformat() if decision else None,
    }


@router.get("/jd/{jd_id}/results")
def get_results(jd_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _get_jd(jd_id, user, db)
    rows = (
        db.query(MatchResult, Resume)
        .join(Resume, MatchResult.resume_id == Resume.id)
        .filter(MatchResult.jd_id == jd_id)
        .order_by(MatchResult.rank)
        .all()
    )
    return [_candidate_out(db, result, resume) for result, resume in rows]


@router.get("/jd/{jd_id}/analytics")
def get_analytics(jd_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    jd = _get_jd(jd_id, user, db)
    rows = (
        db.query(MatchResult, Resume)
        .join(Resume, MatchResult.resume_id == Resume.id)
        .filter(MatchResult.jd_id == jd.id)
        .all()
    )
    statuses = {"shortlisted": 0, "pending": 0, "rejected": 0}
    buckets = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}
    skill_have: dict[str, int] = {}
    total_score = 0.0
    for result, resume in rows:
        statuses[decision_status(db, result.id)] += 1
        bucket = next(b for b in ("0-20", "21-40", "41-60", "61-80", "81-100")
                      if result.score <= int(b.split("-")[1]))
        buckets[bucket] += 1
        total_score += result.score
        have = {m["skill"] for m in (result.matched or [])}
        for skill in have:
            skill_have[skill] = skill_have.get(skill, 0) + 1

    jd_profile = jd.profile or {}
    all_skills = jd_profile.get("must_have_skills", []) + jd_profile.get("nice_to_have_skills", [])
    coverage = [
        {"skill": s, "covered": skill_have.get(s, 0), "total": len(rows)}
        for s in all_skills
    ][:15]
    return {
        "candidates": len(rows),
        "avg_score": round(total_score / len(rows), 1) if rows else 0,
        "status_breakdown": statuses,
        "score_distribution": buckets,
        "skill_coverage": coverage,
    }


def decision_status(db: Session, result_id: int) -> str:
    decision = db.query(Decision).filter(Decision.result_id == result_id).first()
    return decision.status if decision else "pending"


@router.get("/jd/{jd_id}/export")
def export_csv(jd_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    jd = _get_jd(jd_id, user, db)
    rows = (
        db.query(MatchResult, Resume)
        .join(Resume, MatchResult.resume_id == Resume.id)
        .filter(MatchResult.jd_id == jd.id)
        .order_by(MatchResult.rank)
        .all()
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["rank", "candidate", "match_score", "experience_years", "skills", "missing_required", "status", "recruiter_feedback"])
    for result, resume in rows:
        profile = resume.profile or {}
        writer.writerow([
            result.rank,
            profile.get("name") or resume.filename,
            result.score,
            (profile.get("experience", {}) or {}).get("total_years", 0),
            "; ".join((profile.get("skills", {}) or {}).get("technical", [])[:10]),
            "; ".join(m["skill"] for m in result.missing or [] if m["tier"] == "must"),
            decision_status(db, result.id),
            next((d.feedback for d in db.query(Decision).filter(Decision.result_id == result.id)), ""),
        ])
    buffer.seek(0)
    filename = f"shortlist-{jd.title or jd_id}".replace(" ", "-").lower()
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}.csv"'},
    )


class SettingsIn(BaseModel):
    weights: dict[str, float] = Field(default_factory=dict)
    pii_redaction: bool | None = None
    theme: str | None = None


@router.get("/settings")
def get_settings(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = get_user_settings(user, db)
    return {"weights": row.weights or {}, "pii_redaction": row.pii_redaction, "theme": row.theme}


@router.put("/settings")
def update_settings(data: SettingsIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = get_user_settings(user, db)
    if data.weights is not None:
        clean = {k: float(v) for k, v in data.weights.items()
                 if k in ("skills", "experience", "projects", "education", "certifications") and v >= 0}
        if clean:
            row.weights = clean
    if data.pii_redaction is not None:
        row.pii_redaction = data.pii_redaction
    if data.theme in ("light", "dark"):
        row.theme = data.theme
    db.commit()
    return {"weights": row.weights or {}, "pii_redaction": row.pii_redaction, "theme": row.theme}


class DecisionIn(BaseModel):
    status: str = Field(pattern="^(shortlisted|pending|rejected)$")
    feedback: str = Field(default="", pattern="^(relevant|not_relevant|missing_required_skill|)$")
    note: str = Field(default="", max_length=2000)
