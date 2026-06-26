import re
from dataclasses import dataclass

from app.models.analysis import AnalyzeRequest, RequirementMatch, ScoreBreakdownItem, ShortlistingFactor
from app.services.certificate_matcher import best_certificate_match
from app.services.jd_parser import _extract_locations as extract_jd_locations
from app.services.jd_parser import _extract_work_modes as extract_work_modes
from app.services.requirement_matcher import build_requirement_matches


@dataclass
class ScoringResult:
    technical_match_score: int
    interview_readiness_score: int
    shortlisting_score: int
    overall_opportunity_score: int
    score_breakdown: list[ScoreBreakdownItem]
    shortlisting_factors: list[ShortlistingFactor]
    requirement_matches: list[RequirementMatch]
    recommended_action: str


def score_resume_against_jd(request: AnalyzeRequest) -> ScoringResult:
    requirement_matches = build_requirement_matches(request)
    weights = _weights_for_experience(request.candidateContext.experienceYears)
    category_scores = _category_scores(request, requirement_matches)
    breakdown = _build_breakdown(weights, category_scores)
    technical_score = round(sum(item.weightedScore for item in breakdown))
    interview_readiness = _calculate_interview_readiness(technical_score, category_scores)
    shortlisting_score, shortlisting_factors = _calculate_shortlisting_score(request, technical_score)
    overall_score = round((technical_score * 0.45) + (shortlisting_score * 0.30) + (interview_readiness * 0.25))

    return ScoringResult(
        technical_match_score=max(0, min(technical_score, 100)),
        interview_readiness_score=max(0, min(interview_readiness, 100)),
        shortlisting_score=max(0, min(shortlisting_score, 100)),
        overall_opportunity_score=max(0, min(overall_score, 100)),
        score_breakdown=breakdown,
        shortlisting_factors=shortlisting_factors,
        requirement_matches=requirement_matches,
        recommended_action=_recommended_action(technical_score, shortlisting_score, interview_readiness),
    )


def _weights_for_experience(experience_years: int) -> dict[str, int]:
    if experience_years <= 1:
        return {
            "experienceFit": 10,
            "problemSolving": 15,
            "dynamicRequirementFit": 25,
            "projectRelevance": 20,
            "technicalDepth": 15,
            "deliveryReadiness": 10,
            "systemReadiness": 5,
        }
    if experience_years <= 4:
        return {
            "experienceFit": 10,
            "dynamicRequirementFit": 30,
            "projectRelevance": 20,
            "technicalDepth": 15,
            "deliveryReadiness": 15,
            "systemReadiness": 5,
            "problemSolving": 5,
        }
    return {
        "experienceFit": 10,
        "dynamicRequirementFit": 25,
        "architectureReadiness": 20,
        "scalabilityReliability": 15,
        "deliveryReadiness": 10,
        "teamOwnership": 10,
        "domainDepth": 10,
    }


def _category_scores(request: AnalyzeRequest, requirement_matches: list[RequirementMatch]) -> dict[str, tuple[int, str]]:
    resume = f"{request.resumeText} {' '.join(request.candidateContext.currentStack)}"
    experience_score, experience_reason = _experience_score(request)
    dynamic_score = _dynamic_requirement_score(requirement_matches)
    technical_score = _category_requirement_score(requirement_matches, ["technical_requirement"], fallback=dynamic_score)
    responsibility_score = _category_requirement_score(requirement_matches, ["responsibility"], fallback=dynamic_score)
    certification_score = _category_requirement_score(requirement_matches, ["certification"], fallback=dynamic_score)

    certificate_match = best_certificate_match(resume, request.jobDescriptionText)
    certification_aware_score = certificate_match.score if certificate_match else certification_score
    certification_reason = (
        certificate_match.reason
        if certificate_match
        else "Certification and platform-specific requirements are scored from dynamically extracted JD requirements."
    )

    ownership_score = _signal_score(
        resume,
        ["owned", "delivered", "maintained", "released", "improved", "optimized", "end-to-end", "requirements"],
        fallback=responsibility_score,
    )
    delivery_score = _signal_score(
        resume,
        ["production", "debug", "logs", "monitor", "incident", "release", "deployment", "support", "root cause"],
        fallback=responsibility_score,
    )
    system_score = _signal_score(
        resume,
        ["architecture", "design", "scale", "scalable", "distributed", "reliable", "performance", "latency"],
        fallback=technical_score,
    )
    problem_score = _signal_score(
        resume,
        ["problem", "algorithm", "optimized", "debugged", "analysis", "solved", "complexity"],
        fallback=dynamic_score,
    )
    scalability_score = _signal_score(
        resume,
        ["scale", "performance", "monitoring", "reliable", "cache", "queue", "latency", "throughput"],
        fallback=system_score,
    )
    project_score = _project_relevance_score(requirement_matches, ownership_score)
    domain_score = round((dynamic_score + project_score + ownership_score) / 3)

    return {
        "experienceFit": (experience_score, experience_reason),
        "problemSolving": (problem_score, "Problem-solving is inferred from dynamic JD matches plus resume evidence of debugging, optimization, analysis, and algorithms."),
        "dynamicRequirementFit": (dynamic_score, _dynamic_requirement_reason(requirement_matches)),
        "projectRelevance": (project_score, "Projects are scored against dynamic JD requirements and evidence source strength."),
        "technicalDepth": (technical_score, "Technical depth is based on dynamically extracted JD requirements instead of a fixed skill whitelist."),
        "deliveryReadiness": (max(delivery_score, certification_aware_score if certification_score else delivery_score), certification_reason if certification_score else "Delivery readiness checks dynamic responsibilities plus production, release, debugging, and support evidence."),
        "systemReadiness": (system_score, "System readiness is inferred from architecture, design, scale, reliability, and performance evidence."),
        "architectureReadiness": (round((system_score + technical_score) / 2), "Architecture readiness combines dynamic technical fit with design and scalability signals."),
        "scalabilityReliability": (scalability_score, "Scalability and reliability are inferred from performance, monitoring, queueing, caching, and reliability evidence."),
        "teamOwnership": (ownership_score, "Team ownership checks delivery responsibility, ownership wording, and measurable impact signals."),
        "domainDepth": (domain_score, "Domain depth is inferred from dynamic JD fit, project evidence, and ownership depth."),
    }


def _build_breakdown(weights: dict[str, int], category_scores: dict[str, tuple[int, str]]) -> list[ScoreBreakdownItem]:
    breakdown = []
    for category, weight in weights.items():
        score, reason = category_scores[category]
        bounded_score = max(0, min(score, 100))
        breakdown.append(
            ScoreBreakdownItem(
                category=category,
                weight=weight,
                score=bounded_score,
                weightedScore=round((bounded_score * weight) / 100, 2),
                reason=reason,
            )
        )
    return breakdown


def _dynamic_requirement_score(requirement_matches: list[RequirementMatch]) -> int:
    if not requirement_matches:
        return 45
    weighted_total = 0.0
    total_weight = 0.0
    for match in requirement_matches:
        weight = _importance_weight(match.importance)
        weighted_total += match.score * weight
        total_weight += weight
    return round(weighted_total / max(total_weight, 1))


def _category_requirement_score(requirement_matches: list[RequirementMatch], categories: list[str], fallback: int) -> int:
    matches = [match for match in requirement_matches if match.category in categories]
    if not matches:
        return fallback
    return _dynamic_requirement_score(matches)


def _project_relevance_score(requirement_matches: list[RequirementMatch], ownership_score: int) -> int:
    project_or_experience = [
        match.score
        for match in requirement_matches
        if match.evidenceSource in {"project", "experience"} and match.score > 0
    ]
    if not project_or_experience:
        return round((ownership_score + _dynamic_requirement_score(requirement_matches)) / 2)
    return round((sum(project_or_experience) / len(project_or_experience) * 0.7) + (ownership_score * 0.3))


def _dynamic_requirement_reason(requirement_matches: list[RequirementMatch]) -> str:
    if not requirement_matches:
        return "No clear JD requirements were extracted dynamically; score uses a conservative fallback."
    matched = [match.requirement for match in requirement_matches if match.score >= 55]
    missing = [match.requirement for match in requirement_matches if match.score < 35]
    matched_label = ", ".join(matched[:5]) if matched else "no strong dynamic requirement matches"
    missing_label = ", ".join(missing[:5]) if missing else "no major dynamic requirement gaps"
    return f"Dynamically extracted JD matches: {matched_label}. Weak or missing: {missing_label}."


def _importance_weight(importance: str) -> float:
    if importance == "high":
        return 1.25
    if importance == "low":
        return 0.75
    return 1.0


def _signal_score(text: str, signals: list[str], fallback: int) -> int:
    lowered = text.lower()
    hits = sum(1 for signal in signals if signal in lowered)
    if hits == 0:
        return max(30, round(fallback * 0.85))
    return min(95, max(fallback, 42 + hits * 11))


def _experience_score(request: AnalyzeRequest) -> tuple[int, str]:
    min_years, max_years = _extract_experience_range(request.jobDescriptionText)
    candidate_years = request.candidateContext.experienceYears
    if min_years is None:
        return 80, "JD experience range was not explicit; candidate experience is not penalized strongly."
    if candidate_years < min_years:
        gap = min_years - candidate_years
        score = max(25, 75 - (gap * 18))
        return score, f"JD expects at least {min_years} year(s); candidate has {candidate_years} year(s)."
    if max_years is not None and candidate_years > max_years:
        return 70, f"Candidate has {candidate_years} year(s), which is above the JD range of {min_years}-{max_years}."
    return 95, f"Candidate experience of {candidate_years} year(s) fits the JD range."


def _extract_experience_range(text: str) -> tuple[float | None, float | None]:
    lowered = text.lower()
    range_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)", lowered)
    if range_match:
        return float(range_match.group(1)), float(range_match.group(2))
    min_match = re.search(r"(?:minimum|min|at least)\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)", lowered)
    if min_match:
        return float(min_match.group(1)), None
    single_match = re.search(r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)", lowered)
    if single_match:
        return float(single_match.group(1)), None
    return None, None


def _calculate_interview_readiness(technical_score: int, category_scores: dict[str, tuple[int, str]]) -> int:
    weak_topic_penalty = 0
    for topic in ["dynamicRequirementFit", "technicalDepth", "deliveryReadiness", "systemReadiness"]:
        if topic not in category_scores:
            continue
        score, _reason = category_scores[topic]
        if score < 50:
            weak_topic_penalty += 4
    return max(20, min(95, technical_score - weak_topic_penalty))


def _calculate_shortlisting_score(request: AnalyzeRequest, technical_score: int) -> tuple[int, list[ShortlistingFactor]]:
    context = request.candidateContext
    score = round(technical_score * 0.65) + 20
    factors: list[ShortlistingFactor] = []

    experience_score, experience_reason = _experience_score(request)
    if experience_score < 60:
        score -= 12
        factors.append(ShortlistingFactor(factor="Experience range", impact="negative", reason=experience_reason))
    else:
        score += 5
        factors.append(ShortlistingFactor(factor="Experience range", impact="positive", reason=experience_reason))

    if context.noticePeriodDays is not None:
        if context.noticePeriodDays <= 30:
            score += 8
            factors.append(ShortlistingFactor(factor="Notice period", impact="positive", reason="Notice period is within 30 days, which helps urgent hiring."))
        elif context.noticePeriodDays <= 60:
            score -= 2
            factors.append(ShortlistingFactor(factor="Notice period", impact="neutral", reason="60-day notice is common but weaker than immediate or 30-day availability."))
        else:
            score -= 10
            factors.append(ShortlistingFactor(factor="Notice period", impact="negative", reason="Notice period above 60 days can reduce shortlisting for urgent roles."))
    else:
        factors.append(ShortlistingFactor(factor="Notice period", impact="neutral", reason="Notice period was not provided, so it is not used strongly."))

    location_factor = _location_factor(request)
    score += location_factor[0]
    factors.append(location_factor[1])

    work_mode_factor = _work_mode_factor(request)
    score += work_mode_factor[0]
    factors.append(work_mode_factor[1])

    if context.currentCtcLpa and context.expectedCtcLpa:
        hike = ((context.expectedCtcLpa - context.currentCtcLpa) / max(context.currentCtcLpa, 1)) * 100
        if hike <= 60:
            score += 4
            factors.append(ShortlistingFactor(factor="CTC expectation", impact="positive", reason=f"Expected hike is around {round(hike)}%, which is within a commonly negotiable range."))
        elif hike <= 100:
            factors.append(ShortlistingFactor(factor="CTC expectation", impact="neutral", reason=f"Expected hike is around {round(hike)}%; it may need justification through skill fit."))
        else:
            score -= 8
            factors.append(ShortlistingFactor(factor="CTC expectation", impact="negative", reason=f"Expected hike is around {round(hike)}%, which may reduce shortlisting without strong fit."))
    else:
        factors.append(ShortlistingFactor(factor="CTC expectation", impact="neutral", reason="CTC data was not provided."))

    return max(0, min(score, 100)), factors


def _location_factor(request: AnalyzeRequest) -> tuple[int, ShortlistingFactor]:
    context = request.candidateContext
    jd_locations = extract_jd_locations(request.jobDescriptionText)
    candidate_locations = [context.currentLocation or "", *context.preferredLocations]
    candidate_text = " ".join(candidate_locations).lower()

    if not jd_locations:
        return 0, ShortlistingFactor(factor="Location", impact="neutral", reason="JD location was not detected.")
    if any(location.lower() in candidate_text for location in jd_locations):
        return 8, ShortlistingFactor(factor="Location", impact="positive", reason="Candidate location or preference matches the JD location.")
    if context.relocationOpen:
        return 2, ShortlistingFactor(factor="Location", impact="neutral", reason="Location is not a direct match, but relocation is open.")
    return -8, ShortlistingFactor(factor="Location", impact="negative", reason="JD location does not match candidate location/preferences.")


def _work_mode_factor(request: AnalyzeRequest) -> tuple[int, ShortlistingFactor]:
    context = request.candidateContext
    jd_modes = extract_work_modes(request.jobDescriptionText)
    preferences = extract_work_modes("Work mode: " + ", ".join(context.workModePreference))
    if not jd_modes or not preferences:
        return 0, ShortlistingFactor(factor="Work mode", impact="neutral", reason="Work mode was not clear in both JD and candidate preferences.")
    if any(mode in preferences for mode in jd_modes):
        return 5, ShortlistingFactor(factor="Work mode", impact="positive", reason="Candidate work-mode preference matches the JD.")
    return -5, ShortlistingFactor(factor="Work mode", impact="negative", reason="Candidate work-mode preference may not match the JD.")


def _recommended_action(technical_score: int, shortlisting_score: int, interview_readiness: int) -> str:
    if technical_score >= 75 and shortlisting_score >= 70:
        return "Apply actively. Prepare role-specific cross-questions and strengthen weak topics before interviews."
    if technical_score >= 60:
        return "Apply, but treat this as a preparation-heavy opportunity. Improve weak evidence areas before recruiter or technical rounds."
    if interview_readiness < 50:
        return "Do targeted preparation first, then apply selectively. Focus on missing core skills and project explanation depth."
    return "Apply only if the role is flexible on experience and skills; otherwise use this JD as a preparation benchmark."
