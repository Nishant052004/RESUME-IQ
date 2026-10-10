"""Weighted scoring, ranking & explainability (Module 4).

Component scores (each in [0, 1]):
  skills          — coverage of must-have (weight 1.0 each) and nice-to-have
                    (weight 0.5 each) skills from the JD
  experience      — relevant years vs. the JD's minimum (capped at 1.0);
                    when the JD states no minimum, min(years / 3, 1) is used
                    as a neutral prior
  projects        — semantic relevance of the resume's project section to the JD
  education       — degree match; EXCLUDED from the weighted sum (weight
                    redistributed) when the JD lists no degree requirement
  certifications  — same exclusion rule when the JD lists none

The final score is 100 * Σ active_weight × component. Every result stores the
weights used and a human-readable criteria list for transparency (Module 5).
"""
from ..privacy.filters import scoring_criteria


def normalize_weights(weights: dict | None) -> dict[str, float]:
    """Fill missing categories with defaults, then normalize to fractions."""
    defaults = {"skills": 40, "experience": 25, "projects": 15, "education": 10, "certifications": 10}
    merged = dict(defaults)
    if weights:
        for key, value in weights.items():
            if key in defaults and isinstance(value, (int, float)) and value >= 0:
                merged[key] = float(value)
    total = sum(merged.values()) or 1.0
    return {k: v / total for k, v in merged.items()}


def _skills_component(matched: list[dict], missing: list[dict], fallback: float) -> float:
    total_must = sum(1 for m in matched + missing if m["tier"] == "must")
    total_nice = sum(1 for m in matched + missing if m["tier"] == "nice")
    if total_must + total_nice == 0:
        return fallback  # JD lists no detectable skills → semantic similarity proxy
    weight = total_must + 0.5 * total_nice
    got = sum(1 for m in matched if m["tier"] == "must") + 0.5 * sum(1 for m in matched if m["tier"] == "nice")
    return got / weight


def _experience_component(years: float, required: int) -> float:
    if required > 0:
        return min(years / required, 1.0)
    return min(years / 3.0, 1.0)  # neutral prior when the JD states no minimum


def _education_component(resume_education: list[dict], jd_degrees: list[str]) -> float:
    if jd_degrees:
        resume_degrees = {e.get("degree", "").upper() for e in resume_education}
        for jd_degree in jd_degrees:
            for rd in resume_degrees:
                if rd and (rd in jd_degree or jd_degree in rd or rd[:4] == jd_degree[:4]):
                    return 1.0
        return 0.3 if resume_education else 0.0
    return -1.0  # signal: not required → excluded from weighted sum


def _certifications_component(resume_certs: list[str], jd_certs: list[str]) -> float:
    if jd_certs:
        resume_low = [c.lower() for c in resume_certs]
        hits = sum(1 for jc in jd_certs if any(jc.lower()[:12] in rc for rc in resume_low))
        return hits / len(jd_certs)
    return -1.0


def compute_components(resume_profile: dict, jd_profile: dict, match: dict, weights: dict | None = None):
    """Return ({component: score}, {component: active_weight})."""
    experience = resume_profile.get("experience", {}) or {}
    years = float(experience.get("total_years", 0) or 0)
    skills_score = _skills_component(match["matched"], match["missing"], match["similarity"])

    components = {
        "skills": skills_score,
        "experience": _experience_component(years, int(jd_profile.get("min_years_experience", 0) or 0)),
        "projects": float(match.get("project_relevance", 0.0)),
    }

    normalized = normalize_weights(weights)
    education = _education_component(resume_profile.get("education", []), jd_profile.get("education", []))
    certifications = _certifications_component(
        resume_profile.get("certifications", []), jd_profile.get("certifications", [])
    )

    active = dict(normalized)
    if education >= 0:
        components["education"] = education
    else:
        active.pop("education", None)
    if certifications >= 0:
        components["certifications"] = certifications
    else:
        active.pop("certifications", None)

    total_active = sum(active.values()) or 1.0
    active = {k: v / total_active for k, v in active.items()}
    return components, active


def explain(resume_profile: dict, jd_profile: dict, match: dict, components: dict) -> dict:
    """Explainable-AI output: why matched / what's missing / evidence / criteria."""
    why: list[str] = []
    years = float((resume_profile.get("experience", {}) or {}).get("total_years", 0) or 0)
    required = int(jd_profile.get("min_years_experience", 0) or 0)
    if required and years >= required:
        why.append(f"{years:g} years of experience meets the {required}+ year requirement.")
    elif years:
        why.append(f"{years:g} years of total experience.")
    for item in match["matched"][:5]:
        label = "Required skill" if item["tier"] == "must" else "Nice-to-have skill"
        if item.get("evidence"):
            why.append(f"{label} — {item['skill']}: “{item['evidence'][0]}”")
        else:
            why.append(f"{label} — {item['skill']} found in the resume.")

    missing = [m["skill"] for m in match["missing"] if m["tier"] == "must"]
    missing_nice = [m["skill"] for m in match["missing"] if m["tier"] == "nice"]
    if not match["matched"] and not match["missing"]:
        why.append("The job description lists no explicit skills; the score is based on overall semantic similarity.")

    evidence = []
    for quotes in resume_profile.get("skill_evidence", {}).values():
        evidence.extend(quotes)
    evidence = evidence[:4]

    weights_pct = {k: round(v * 100) for k, v in components.items()}
    return {
        "why_matched": why[:8],
        "missing_required": missing,
        "missing_nice_to_have": missing_nice,
        "evidence": evidence,
        "criteria": scoring_criteria(weights_pct, jd_profile),
    }


def score_resume(resume_profile: dict, match: dict, jd_profile: dict, weights: dict | None = None) -> dict:
    components, active_weights = compute_components(resume_profile, jd_profile, match, weights)
    final = round(100 * sum(active_weights[k] * v for k, v in components.items()), 1)
    return {
        "score": final,
        "subscores": {k: round(v, 3) for k, v in components.items()},
        "active_weights": {k: round(v, 4) for k, v in active_weights.items()},
        "matched": match["matched"],
        "missing": match["missing"],
        "explanation": explain(resume_profile, jd_profile, match, active_weights),
    }
