"""Semantic matching engine (Module 3).

Pipeline:
1. Alias normalization — every skill alias ("React.js", "Postgres", "K8s") is
   rewritten to its canonical token before any vectorization, so related terms
   resolve to the same concept.
2. TF-IDF vectorization (word 1-2 grams) + cosine similarity between the JD
   and the resume → a semantic similarity in [0, 1] that goes beyond exact
   keyword overlap.
3. Requirement matching — every must-have / nice-to-have skill detected in the
   JD is marked matched (with quoted evidence from the resume) or missing.

The engine is deterministic and dependency-light (scikit-learn only). When an
LLM key is configured the same outputs can optionally be refined, but nothing
requires network access.
"""
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ..extraction.lexicon import ALIAS_INDEX

# Sort longest-first so "react native" is rewritten before "react", "rest api"
# before "rest".
_ALIAS_RULES = sorted(ALIAS_INDEX.items(), key=lambda kv: len(kv[0]), reverse=True)
_ALIAS_PATTERNS = [
    (re.compile(r"(?<![A-Za-z0-9+#])" + re.escape(alias) + r"(?![A-Za-z0-9+#])", re.IGNORECASE), canonical)
    for alias, canonical in _ALIAS_RULES
]


def normalize_text(text: str) -> str:
    for pattern, canonical in _ALIAS_PATTERNS:
        text = pattern.sub(canonical, text)
    return text


def tfidf_similarity(source: str, target: str) -> float:
    """Cosine similarity between two texts, in [0, 1]."""
    source, target = normalize_text(source).lower(), normalize_text(target).lower()
    if not source.strip() or not target.strip():
        return 0.0
    try:
        vectors = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, stop_words="english")
        matrix = vectors.fit_transform([source, target])
    except ValueError:  # e.g. both texts contain only stop words
        return 0.0
    return round(float(cosine_similarity(matrix[0], matrix[1])[0][0]), 4)


def match_requirements(resume_profile: dict, jd_profile: dict) -> tuple[list[dict], list[dict]]:
    """Compare JD requirements with the resume's detected skills."""
    resume_skills = set(resume_profile.get("skills", {}).get("technical", []))
    evidence = resume_profile.get("skill_evidence", {})

    matched, missing = [], []
    for tier, key in (("must", "must_have_skills"), ("nice", "nice_to_have_skills")):
        for skill in jd_profile.get(key, []):
            if skill in resume_skills:
                matched.append({"skill": skill, "tier": tier, "evidence": evidence.get(skill, [])[:1]})
            else:
                missing.append({"skill": skill, "tier": tier})
    return matched, missing


def analyze_match(resume_text: str, resume_profile: dict, jd_text: str, jd_profile: dict) -> dict:
    """Full match analysis for one resume against one JD."""
    matched, missing = match_requirements(resume_profile, jd_profile)

    project_text = "\n".join(
        f"{p.get('title', '')} {p.get('detail', '')}" for p in resume_profile.get("projects", [])
    ).strip()
    # Best single project wins (a concatenated blob dilutes relevance), and the
    # raw cosine is calibrated up: short project blurbs systematically score in
    # the 0-0.3 cosine band even when clearly relevant.
    relevance = 0.0
    for project in resume_profile.get("projects", []):
        blurb = f"{project.get('title', '')} {project.get('detail', '')}".strip()
        if blurb:
            relevance = max(relevance, tfidf_similarity(blurb, jd_text))
    return {
        "similarity": tfidf_similarity(resume_text, jd_text),
        "project_relevance": min(1.0, relevance * 3.0) if relevance else 0.0,
        "matched": matched,
        "missing": missing,
    }
