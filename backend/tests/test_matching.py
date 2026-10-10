"""Module 3 tests — semantic matching & related-term resolution."""
from app.extraction.engine import build_jd_profile, build_resume_profile
from app.matching.engine import analyze_match, normalize_text, tfidf_similarity

JD = """Backend Engineer
Requirements:
- 3+ years of Python experience
- FastAPI and PostgreSQL
- Docker
"""


def test_alias_normalization_maps_related_terms():
    normalized = normalize_text("Built APIs with React.js, Postgres and K8s")
    assert "react" in normalized.lower()
    assert "postgresql" in normalized.lower()
    assert "kubernetes" in normalized.lower()
    assert "react.js" not in normalized.lower()


def test_similarity_bounds_and_ordering():
    strong = "We need Python FastAPI PostgreSQL Docker" * 3
    unrelated = "Sales representative with fashion retail experience"
    jd = "Python FastAPI PostgreSQL Docker backend"
    assert 0.0 <= tfidf_similarity(strong, jd) <= 1.0
    assert tfidf_similarity(strong, jd) > tfidf_similarity(unrelated, jd)


def test_identical_texts_score_one():
    text = "Python FastAPI PostgreSQL Docker backend engineering"
    assert tfidf_similarity(text, text) == 1.0


def test_empty_text_scores_zero():
    assert tfidf_similarity("", "python backend") == 0.0
    assert tfidf_similarity("python backend", "") == 0.0


def test_requirement_matching_marks_matched_and_missing():
    resume = """Aditi Rao
aditi.rao@example.com

SUMMARY
Python developer with 4 years of experience.

EXPERIENCE
Developer at Zoho | Jan 2020 - Present
- Built FastAPI REST APIs with PostgreSQL
- Deployed with Docker

SKILLS
Python, FastAPI, PostgreSQL, Docker, Redis
"""
    profile = build_resume_profile(resume)
    jd_profile = build_jd_profile(JD)
    match = analyze_match(resume, profile, JD, jd_profile)
    matched = {m["skill"] for m in match["matched"]}
    assert {"python", "fastapi", "postgresql", "docker"}.issubset(matched)
    assert match["matched"][0]["evidence"], "matched skills must carry quoted evidence"
    missing = {m["skill"] for m in match["missing"]}
    assert not (matched & missing), "a skill cannot be both matched and missing"


def test_related_term_resolves_missing_requirement():
    # Resume says 'Postgres' (alias), JD says 'PostgreSQL' — must still match.
    resume = "SKILLS\nPython, Django, Postgres, Docker"
    profile = build_resume_profile(resume)
    jd_profile = build_jd_profile(JD)
    match = analyze_match(resume, profile, JD, jd_profile)
    assert "postgresql" in {m["skill"] for m in match["matched"]}
