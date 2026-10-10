"""Ingestion API (Module 1): job descriptions + resume uploads."""
import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth.deps import get_current_user, get_user_settings
from ..database import get_db
from ..extraction.engine import build_jd_profile, build_resume_profile
from ..models import JobDescription, Resume, User
from ..privacy.filters import strip_protected_attributes
from ..privacy.pii import redact_text
from .extractors import extract_text

router = APIRouter(prefix="/api", tags=["ingestion"])
MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB per file


class JDIn(BaseModel):
    title: str = ""
    company: str = ""
    text: str = Field(min_length=30, description="Paste the full job description text.")


def _jd_out(jd: JobDescription) -> dict:
    return {
        "id": jd.id,
        "title": jd.title,
        "company": jd.company,
        "created_at": jd.created_at.isoformat(),
        "profile": jd.profile,
        "text_length": len(jd.raw_text),
    }


@router.post("/jd", status_code=201)
def create_jd(data: JDIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = build_jd_profile(data.text)
    jd = JobDescription(
        user_id=user.id,
        title=data.title.strip() or profile["title"],
        company=data.company.strip(),
        raw_text=data.text,
        profile=profile,
    )
    db.add(jd)
    db.commit()
    db.refresh(jd)
    return _jd_out(jd)


@router.get("/jd")
def list_jds(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    jds = db.query(JobDescription).filter(JobDescription.user_id == user.id).order_by(JobDescription.created_at.desc()).all()
    return [_jd_out(j) for j in jds]


@router.get("/jd/{jd_id}")
def get_jd(jd_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    jd = db.get(JobDescription, jd_id)
    if jd is None or jd.user_id != user.id:
        raise HTTPException(status_code=404, detail="Job description not found.")
    return _jd_out(jd)


@router.delete("/jd/{jd_id}", status_code=204)
def delete_jd(jd_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    jd = db.get(JobDescription, jd_id)
    if jd is None or jd.user_id != user.id:
        raise HTTPException(status_code=404, detail="Job description not found.")
    # Resumes stay reusable across JDs, so only the JD row is removed.
    db.delete(jd)
    db.commit()


@router.post("/resumes/upload")
async def upload_resumes(
    files: list[UploadFile] = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Batch upload. Every file reports its own status so one bad file never
    fails the whole batch (per-file parsing status, as in the UI prototype)."""
    settings_row = get_user_settings(user, db)
    report = []
    for upload in files:
        data = await upload.read()
        filename = os.path.basename(upload.filename or "upload")
        if not data:
            report.append({"filename": filename, "status": "error", "error": "Empty file."})
            continue
        if len(data) > MAX_FILE_BYTES:
            report.append({"filename": filename, "status": "error", "error": "File exceeds the 10 MB limit."})
            continue
        try:
            text = extract_text(filename, data)
        except Exception as exc:  # unreadable/corrupt file → per-file failure
            report.append({"filename": filename, "status": "error", "error": f"Could not extract text: {exc}"})
            continue

        if settings_row.pii_redaction:
            # Module 5: redact PII + strip protected attributes BEFORE storage.
            text = strip_protected_attributes(redact_text(text))

        profile = build_resume_profile(text)
        resume = Resume(
            user_id=user.id,
            filename=filename,
            content_type=upload.content_type or "",
            raw_text=text,
            profile=profile,
        )
        db.add(resume)
        db.commit()
        db.refresh(resume)
        report.append({
            "filename": filename,
            "status": "parsed",
            "resume_id": resume.id,
            "candidate_name": profile.get("name") or filename.rsplit(".", 1)[0],
            "skills_found": len(profile.get("skills", {}).get("technical", [])),
            "experience_years": profile.get("experience", {}).get("total_years", 0),
        })
    return {"uploaded": sum(1 for r in report if r["status"] == "parsed"), "files": report}


def _resume_out(resume: Resume) -> dict:
    profile = resume.profile or {}
    return {
        "id": resume.id,
        "filename": resume.filename,
        "candidate_name": profile.get("name") or resume.filename.rsplit(".", 1)[0],
        "skills": profile.get("skills", {}),
        "experience_years": (profile.get("experience", {}) or {}).get("total_years", 0),
        "companies": [r.get("company") for r in (profile.get("experience", {}) or {}).get("roles", []) if r.get("company")],
        "education": profile.get("education", []),
        "certifications": profile.get("certifications", []),
        "created_at": resume.created_at.isoformat(),
    }


@router.get("/resumes")
def list_resumes(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resumes = db.query(Resume).filter(Resume.user_id == user.id).order_by(Resume.created_at.desc()).all()
    return [_resume_out(r) for r in resumes]


@router.delete("/resumes/{resume_id}", status_code=204)
def delete_resume(resume_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resume = db.get(Resume, resume_id)
    if resume is None or resume.user_id != user.id:
        raise HTTPException(status_code=404, detail="Resume not found.")
    db.delete(resume)
    db.commit()
