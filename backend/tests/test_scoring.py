"""Module 4 tests — weighted scoring, ranking & explainability."""
from app.extraction.engine import build_jd_profile, build_resume_profile
from app.matching.engine import analyze_match
from app.scoring.engine import normalize_weights, score_resume

JD = """Senior Python Backend Engineer

Requirements:
- 4+ years of Python experience
- FastAPI and PostgreSQL
- Docker
"""

STRONG = """Ananya Singh
ananya@example.com

SUMMARY
Backend engineer with 6 years of Python experience.

EXPERIENCE
Senior Engineer at Razorpay | Jan 2019 - Present
- Built FastAPI REST APIs with PostgreSQL
- Deployed services with Docker and Kubernetes

SKILLS
Python, FastAPI, PostgreSQL, Docker, Kubernetes, Redis

EDUCATION
B.Tech in Computer Science, NIT Trichy, 2018
"""

WEAK = """Blah Blah
Sales associate, retail store experience, two years.

EXPERIENCE
Sales Associate at Store | Jan 2022 - Present
- Helped customers

SKILLS
Communication, Excel
"""


def _score(text, weights=None):
    profile = build_resume_profile(text)
    jd_profile = build_jd_profile(JD)
    match = analyze_match(text, profile, JD, jd_profile)
    return score_resume(profile, match, jd_profile, weights)


def test_weights_normalize_to_one():
    weights = normalize_weights({"skills": 50, "experience": 30, "projects": 20, "education": 0, "certifications": 0})
    assert abs(sum(weights.values()) - 1.0) < 1e-9
    assert weights["skills"] == 0.5


def test_weights_fill_missing_categories_with_defaults():
    weights = normalize_weights({"skills": 100})
    assert abs(sum(weights.values()) - 1.0) < 1e-9
    assert all(k in weights for k in ("experience", "projects", "education", "certifications"))


def test_strong_candidate_outranks_weak_one():
    assert _score(STRONG)["score"] > _score(WEAK)["score"] + 20


def test_scores_stay_in_bounds():
    for text in (STRONG, WEAK, ""):
        result = _score(text)
        assert 0.0 <= result["score"] <= 100.0


def test_empty_resume_edge_case_does_not_crash():
    result = _score("")
    assert result["score"] == 0.0
    assert result["explanation"]["missing_required"]


def test_weights_change_the_score_of_an_asymmetric_candidate():
    # Neha maxes the skills axis but is a fresher on the experience axis, so
    # her score MUST move when the weight moves from skills to experience.
    neha = """Neha Jain
neha@example.com

SUMMARY
Python developer with 1 year of experience.

EXPERIENCE
Developer at Swiggy | Jan 2026 - Present
- Built FastAPI REST APIs with PostgreSQL, deployed with Docker

SKILLS
Python, FastAPI, PostgreSQL, Docker, Redis
"""
    skills_heavy = {"skills": 80, "experience": 10, "projects": 5, "education": 2.5, "certifications": 2.5}
    exp_heavy = {"skills": 10, "experience": 80, "projects": 5, "education": 2.5, "certifications": 2.5}
    assert _score(neha, skills_heavy)["score"] > _score(neha, exp_heavy)["score"] + 20


def test_ranking_flip_between_candidates_with_different_profiles():
    high_exp_low_skills = """Vikram Rao
vikram@example.com

EXPERIENCE
Engineer at Oracle | Jan 2016 - Present
- Maintained legacy Java systems and SQL databases

SKILLS
Java, SQL, Git
"""
    low_exp_high_skills = """Neha Jain
neha@example.com

SUMMARY
Python developer, fresh graduate.

EXPERIENCE
Developer Intern at Swiggy | Jun 2026 - Present
- Built FastAPI REST APIs with PostgreSQL, deployed with Docker

SKILLS
Python, FastAPI, PostgreSQL, Docker, Redis
"""
    skills_heavy = {"skills": 80, "experience": 10, "projects": 5, "education": 2.5, "certifications": 2.5}
    exp_heavy = {"skills": 10, "experience": 80, "projects": 5, "education": 2.5, "certifications": 2.5}
    # Under experience-heavy weights the veteran ranks first…
    assert _score(high_exp_low_skills, exp_heavy)["score"] > _score(low_exp_high_skills, exp_heavy)["score"]
    # …and the order REVERSES under skills-heavy weights.
    assert _score(low_exp_high_skills, skills_heavy)["score"] > _score(high_exp_low_skills, skills_heavy)["score"]


def test_explanation_quotes_come_from_the_resume_no_hallucination():
    result = _score(STRONG)
    profile = build_resume_profile(STRONG)
    lower_resume = STRONG.lower()
    for quote in result["explanation"]["evidence"]:
        assert quote.lower()[:40] in lower_resume, f"evidence not found in resume: {quote}"
    for skill in {m["skill"] for m in result["matched"]}:
        assert skill in {s for s in profile["skills"]["technical"]}
    for skill in result["explanation"]["missing_required"]:
        assert skill not in profile["skills"]["technical"]


def test_criteria_transparency_is_present():
    result = _score(STRONG)
    criteria = result["explanation"]["criteria"]
    assert any("weight" in c for c in criteria)
    assert any("Protected attributes" in c for c in criteria)
