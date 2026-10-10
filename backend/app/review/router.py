"""Human-in-the-loop review API (Module 7).

Recruiter decisions are stored in their own table — the AI's score on
`match_results` is never modified by a decision, so overrides stay auditable
and the feedback loop (relevant / not relevant / missing required skill) can
later be used to tune the model.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth.deps import get_current_user
from ..database import get_db
from ..models import Decision, JobDescription, MatchResult, Resume, User
from ..scoring.router import DecisionIn

router = APIRouter(prefix="/api", tags=["review"])


@router.post("/results/{result_id}/decision")
def record_decision(
    result_id: int,
    data: DecisionIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = (
        db.query(MatchResult, Resume, JobDescription)
        .join(Resume, MatchResult.resume_id == Resume.id)
        .join(JobDescription, MatchResult.jd_id == JobDescription.id)
        .filter(MatchResult.id == result_id, JobDescription.user_id == user.id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Match result not found.")
    _, resume, jd = row

    decision = db.query(Decision).filter(Decision.result_id == result_id).first()
    if decision is None:
        decision = Decision(result_id=result_id, user_id=user.id)
        db.add(decision)
    decision.status = data.status
    decision.feedback = data.feedback
    decision.note = data.note
    db.commit()
    db.refresh(decision)

    result = db.get(MatchResult, result_id)
    return {
        "result_id": result_id,
        "candidate": (resume.profile or {}).get("name") or resume.filename,
        "jd": jd.title,
        "decision": {"status": decision.status, "feedback": decision.feedback, "note": decision.note},
        # The immutable AI score, returned for contrast with the human decision.
        "ai_score": result.score,
    }


@router.get("/review/activity")
def recent_activity(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(Decision, MatchResult, Resume, JobDescription)
        .join(MatchResult, Decision.result_id == MatchResult.id)
        .join(Resume, MatchResult.resume_id == Resume.id)
        .join(JobDescription, MatchResult.jd_id == JobDescription.id)
        .filter(Decision.user_id == user.id)
        .order_by(Decision.updated_at.desc())
        .limit(12)
        .all()
    )
    return [
        {
            "candidate": (resume.profile or {}).get("name") or resume.filename,
            "jd_title": jd.title,
            "ai_score": result.score,
            "status": decision.status,
            "feedback": decision.feedback,
            "note": decision.note,
            "at": decision.updated_at.isoformat(),
        }
        for decision, result, resume, jd in rows
    ]
