"""Module 2 tests — information extraction."""
from app.extraction.engine import (
    build_jd_profile,
    build_resume_profile,
    find_skills,
    split_sections,
)

RESUME = """Ravi Kumar
Backend Developer

Email: ravi.kumar@example.com | Phone: +91 98200 11223

SUMMARY
Backend developer with 5 years of experience in Python and REST APIs.

EXPERIENCE
Senior Software Engineer at Freshworks | Jan 2020 - Present
- Built FastAPI services with PostgreSQL, improved throughput by 30%

Software Engineer at Infosys | Jun 2017 - Dec 2019
- Django development, automated deployments with Docker

SKILLS
Python, FastAPI, Django, PostgreSQL, Redis, Docker, Git, Communication

PROJECTS
Invoice Service
- FastAPI microservice with PostgreSQL and Docker

EDUCATION
B.Tech in Computer Science, VIT Vellore, 2017

CERTIFICATIONS
AWS Certified Solutions Architect – Associate
"""


def test_section_splitting():
    sections = split_sections(RESUME)
    assert "experience" in sections and "education" in sections
    assert "FastAPI" in sections["experience"] or "Freshworks" in sections["experience"]
    assert "VIT" in sections["education"]


def test_skill_extraction_with_aliases_and_implication():
    skills = find_skills("Built REST APIs with React.js and Postgres; deployed on K8s")
    technical = skills["technical"]
    assert "react" in technical          # react.js alias
    assert "postgresql" in technical     # postgres alias
    assert "kubernetes" in technical     # k8s alias
    assert "javascript" in technical     # react → javascript implication
    assert "sql" in technical            # postgresql → sql implication


def test_experience_years_from_date_ranges():
    profile = build_resume_profile(RESUME)
    years = profile["experience"]["total_years"]
    # Jun 2017 → Dec 2019 (2.5y) + Jan 2020 → now (6+y); allow generous bounds.
    assert 7.0 <= years <= 10.5, f"unexpected years: {years}"
    roles = profile["experience"]["roles"]
    assert any("Freshworks" in r["company"] for r in roles)


def test_education_and_certifications():
    profile = build_resume_profile(RESUME)
    assert any("B.TECH" in e["degree"].upper() for e in profile["education"])
    assert any("AWS" in c for c in profile["certifications"])


def test_contact_extraction():
    profile = build_resume_profile(RESUME)
    assert profile["contact"]["emails"] == ["ravi.kumar@example.com"]
    assert profile["contact"]["phones"], "phone should be detected"


def test_achievements_capture_quantified_impact():
    profile = build_resume_profile(RESUME)
    assert any("30%" in a for a in profile["achievements"])


def test_jd_profile_requirements():
    jd = """Senior Python Developer

Requirements:
- 5+ years of experience with Python
- Strong FastAPI and PostgreSQL skills
- REST API design experience
- Docker deployment experience

Nice to have:
- Kubernetes, Terraform
"""
    profile = build_jd_profile(jd)
    assert profile["min_years_experience"] == 5
    assert {"python", "fastapi", "postgresql"}.issubset(set(profile["must_have_skills"]))
    assert "kubernetes" in profile["nice_to_have_skills"]
    assert "terraform" in profile["nice_to_have_skills"]


def test_empty_and_garbage_input_do_not_crash():
    for text in ["", "   ", "!!!", "a"]:
        profile = build_resume_profile(text)
        assert isinstance(profile, dict)
        assert profile["experience"]["total_years"] == 0


def test_name_guessing():
    profile = build_resume_profile(RESUME)
    assert profile["name"] == "Ravi Kumar"
