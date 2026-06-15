import re
from dataclasses import dataclass

from app.models.analysis import AnalyzeRequest, ScoreBreakdownItem, ShortlistingFactor


@dataclass
class ScoringResult:
    technical_match_score: int
    interview_readiness_score: int
    shortlisting_score: int
    overall_opportunity_score: int
    score_breakdown: list[ScoreBreakdownItem]
    shortlisting_factors: list[ShortlistingFactor]
    recommended_action: str


SKILL_ALIASES: dict[str, list[str]] = {
    ".NET": [".net", "dotnet"],
    "ASP.NET Core": ["asp.net core", "asp net core"],
    "ASP.NET MVC": ["asp.net mvc", "mvc"],
    "C#": ["c#"],
    "Java": ["java", "spring boot"],
    "Python": ["python", "django", "fastapi"],
    "Web API": ["web api", "rest api", "restapi", "restful", "api integration", "apis"],
    "SQL Server": ["sql server", "ssms"],
    "SQL": ["sql", "database", "dbms"],
    "SQLite": ["sqlite", "sqlite3"],
    "Entity Framework": ["entity framework", "ef core", "ef"],
    "LINQ": ["linq"],
    "Angular": ["angular"],
    "React": ["react", "reactjs"],
    "JavaScript": ["javascript", "js", "jquery"],
    "Azure": ["azure", "azure cloud", "app service", "azure sql"],
    "Azure DevOps": ["azure devops", "ci/cd", "pipeline", "build pipeline", "release pipeline"],
    "Azure Fundamentals": ["azure fundamentals", "az-900"],
    "AWS Certification": ["aws certified", "aws certification"],
    "Microsoft Certification": ["microsoft certified", "microsoft certification"],
    "Certification": ["certification", "certified", "certificate"],
    "Docker": ["docker", "container"],
    "Authentication": ["jwt", "authentication", "authorization", "oauth"],
    "DSA": ["dsa", "leetcode", "codechef", "geeksforgeeks", "hackerRank"],
    "System Design": ["system design", "scalable", "architecture", "cache", "queue", "distributed"],
    "Production Debugging": ["production", "debug", "logs", "monitor", "incident", "root cause"],
}


def score_resume_against_jd(request: AnalyzeRequest) -> ScoringResult:
    resume_text = request.resumeText
    jd_text = request.jobDescriptionText
    context = request.candidateContext
    combined_resume = f"{resume_text} {' '.join(context.currentStack)}"
    jd_skills = _extract_skills(jd_text)
    resume_skills = _extract_skills(combined_resume)
    weights = _weights_for_experience(context.experienceYears)

    category_scores = _category_scores(
        request=request,
        jd_skills=jd_skills,
        resume_skills=resume_skills,
    )
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
        recommended_action=_recommended_action(technical_score, shortlisting_score, interview_readiness),
    )


def _weights_for_experience(experience_years: int) -> dict[str, int]:
    if experience_years <= 1:
        return {
            "experienceFit": 10,
            "dsaProblemSolving": 15,
            "coreSkills": 20,
            "projectRelevance": 20,
            "databaseDepth": 10,
            "backendFrontendBasics": 15,
            "cloudDevOps": 5,
            "systemDesignReadiness": 5,
        }
    if experience_years <= 4:
        return {
            "experienceFit": 10,
            "projectOwnership": 20,
            "backendFrontendDepth": 20,
            "databaseDepth": 15,
            "debuggingProduction": 15,
            "cloudDevOps": 10,
            "systemDesignReadiness": 5,
            "dsaProblemSolving": 5,
        }
    return {
        "experienceFit": 10,
        "architecture": 20,
        "systemDesignReadiness": 20,
        "scalabilityReliability": 15,
        "cloudDevOps": 10,
        "teamOwnership": 10,
        "domainDepth": 10,
        "coding": 5,
    }


def _category_scores(request: AnalyzeRequest, jd_skills: set[str], resume_skills: set[str]) -> dict[str, tuple[int, str]]:
    resume = f"{request.resumeText} {' '.join(request.candidateContext.currentStack)}"
    jd = request.jobDescriptionText
    matched_skills = sorted(jd_skills & resume_skills)
    missing_skills = sorted(jd_skills - resume_skills)
    skill_ratio = len(matched_skills) / max(len(jd_skills), 1)
    semantic_ratio = _semantic_phrase_overlap(resume, jd)
    experience_score, experience_reason = _experience_score(request)

    core_score = round((skill_ratio * 75) + (semantic_ratio * 25))
    core_reason = _skill_reason(matched_skills, missing_skills)
    database_score = _topic_score(resume, jd, ["SQL", "SQL Server", "Entity Framework", "LINQ"], fallback=45)
    cloud_score = _topic_score(
        resume,
        jd,
        ["Azure", "Azure DevOps", "Docker", "Azure Fundamentals", "AWS Certification", "Microsoft Certification", "Certification"],
        fallback=35,
    )
    system_score = _topic_score(resume, jd, ["System Design"], fallback=35)
    dsa_score = _topic_score(resume, jd, ["DSA"], fallback=45)
    backend_frontend_score = _topic_score(
        resume,
        jd,
        ["ASP.NET Core", "ASP.NET MVC", "C#", "Web API", "Angular", "React", "JavaScript"],
        fallback=50,
    )
    debugging_score = _topic_score(resume, jd, ["Production Debugging"], fallback=45)
    ownership_score = _ownership_score(resume)
    architecture_score = max(system_score - 5, 25)
    scalability_score = _keyword_presence_score(resume, ["scalable", "performance", "indexing", "caching", "queue", "monitoring"])

    return {
        "experienceFit": (experience_score, experience_reason),
        "dsaProblemSolving": (dsa_score, "Coding-platform and DSA evidence from the resume is evaluated against experience-level expectations."),
        "coreSkills": (core_score, core_reason),
        "projectRelevance": (round((backend_frontend_score * 0.55) + (ownership_score * 0.45)), "Projects are scored for role-relevant implementation, stack overlap, and ownership evidence."),
        "databaseDepth": (database_score, "Database score checks SQL, indexing, ORM, LINQ, transactions, and query optimization signals."),
        "backendFrontendBasics": (backend_frontend_score, "Checks practical fullstack basics: APIs, C#, ASP.NET, frontend integration, and JavaScript framework exposure."),
        "projectOwnership": (ownership_score, "Ownership score looks for end-to-end delivery, production work, measurable impact, and responsibility depth."),
        "backendFrontendDepth": (backend_frontend_score, "Checks deeper backend/frontend role alignment against the JD and resume evidence."),
        "debuggingProduction": (debugging_score, "Production-readiness checks debugging, monitoring, logs, support, and root-cause evidence."),
        "cloudDevOps": (cloud_score, "Cloud/DevOps score checks Azure, CI/CD, pipelines, deployment, Docker, release ownership, and cloud/vendor certifications."),
        "systemDesignReadiness": (system_score, "System design readiness checks architecture, scaling, caching, queues, reliability, and distributed-system signals."),
        "architecture": (architecture_score, "Senior-level architecture score checks design decisions, boundaries, scalability, and ownership beyond implementation."),
        "scalabilityReliability": (scalability_score, "Scalability score checks performance, monitoring, indexing, caching, queues, and reliability evidence."),
        "teamOwnership": (ownership_score, "Team ownership checks mentoring, leading, delivery responsibility, and cross-functional coordination signals."),
        "domainDepth": (round((core_score + ownership_score) / 2), "Domain depth is inferred from role-relevant skills plus project ownership evidence."),
        "coding": (round((core_score + dsa_score) / 2), "Coding score combines core language fit and explicit problem-solving evidence."),
    }


def _build_breakdown(weights: dict[str, int], category_scores: dict[str, tuple[int, str]]) -> list[ScoreBreakdownItem]:
    breakdown = []
    for category, weight in weights.items():
        score, reason = category_scores[category]
        breakdown.append(
            ScoreBreakdownItem(
                category=category,
                weight=weight,
                score=max(0, min(score, 100)),
                weightedScore=round((max(0, min(score, 100)) * weight) / 100, 2),
                reason=reason,
            )
        )
    return breakdown


def _extract_skills(text: str) -> set[str]:
    lowered = text.lower()
    found = set()
    for canonical, aliases in SKILL_ALIASES.items():
        for alias in aliases:
            if _contains_phrase(lowered, alias.lower()):
                found.add(canonical)
                break
    return found


def _contains_phrase(text: str, phrase: str) -> bool:
    escaped = re.escape(phrase).replace("\\ ", r"\s+")
    return bool(re.search(rf"(?<![a-z0-9+#]){escaped}(?![a-z0-9+#])", text))


def _semantic_phrase_overlap(resume_text: str, jd_text: str) -> float:
    resume_phrases = _important_phrases(resume_text)
    jd_phrases = _important_phrases(jd_text)
    if not jd_phrases:
        return 0
    overlap = resume_phrases & jd_phrases
    return len(overlap) / len(jd_phrases)


def _important_phrases(text: str) -> set[str]:
    words = [
        word
        for word in re.findall(r"[a-zA-Z][a-zA-Z+#.]{1,}", text.lower())
        if word not in {"and", "the", "with", "for", "from", "this", "that", "have", "will", "are", "using"}
    ]
    phrases = set(words)
    phrases.update(" ".join(words[index : index + 2]) for index in range(max(0, len(words) - 1)))
    return phrases


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


def _extract_experience_range(text: str) -> tuple[int | None, int | None]:
    lowered = text.lower()
    range_match = re.search(r"(\d+)\s*(?:-|to)\s*(\d+)\s*(?:years?|yrs?)", lowered)
    if range_match:
        return int(range_match.group(1)), int(range_match.group(2))
    min_match = re.search(r"(?:minimum|min|at least)\s*(\d+)\s*(?:years?|yrs?)", lowered)
    if min_match:
        return int(min_match.group(1)), None
    single_match = re.search(r"(\d+)\+?\s*(?:years?|yrs?)", lowered)
    if single_match:
        return int(single_match.group(1)), None
    return None, None


def _skill_reason(matched_skills: list[str], missing_skills: list[str]) -> str:
    matched = ", ".join(matched_skills[:8]) if matched_skills else "no direct core skill matches"
    missing = ", ".join(missing_skills[:6]) if missing_skills else "no major extracted JD skills missing"
    return f"Matched extracted JD skills: {matched}. Missing or weakly evidenced skills: {missing}."


def _topic_score(resume: str, jd: str, skills: list[str], fallback: int) -> int:
    resume_skills = _extract_skills(resume)
    jd_skills = _extract_skills(jd)
    relevant = [skill for skill in skills if skill in jd_skills or skill in resume_skills]
    if not relevant:
        return fallback
    matched = [skill for skill in relevant if skill in resume_skills]
    return round((len(matched) / len(relevant)) * 90) if matched else 30


def _ownership_score(resume: str) -> int:
    signals = ["end-to-end", "delivered", "owned", "maintained", "production", "optimized", "improved", "20+", "requirements"]
    return _keyword_presence_score(resume, signals)


def _keyword_presence_score(text: str, keywords: list[str]) -> int:
    lowered = text.lower()
    hits = sum(1 for keyword in keywords if keyword.lower() in lowered)
    if hits == 0:
        return 30
    return min(95, 40 + hits * 12)


def _calculate_interview_readiness(technical_score: int, category_scores: dict[str, tuple[int, str]]) -> int:
    weak_topic_penalty = 0
    for topic in ["cloudDevOps", "systemDesignReadiness", "databaseDepth", "debuggingProduction"]:
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
    jd_locations = _extract_locations(request.jobDescriptionText)
    candidate_locations = [context.currentLocation or "", *context.preferredLocations]
    candidate_text = " ".join(candidate_locations).lower()

    if not jd_locations:
        return 0, ShortlistingFactor(factor="Location", impact="neutral", reason="JD location was not detected.")
    if any(location in candidate_text for location in jd_locations):
        return 8, ShortlistingFactor(factor="Location", impact="positive", reason="Candidate location or preference matches the JD location.")
    if context.relocationOpen:
        return 2, ShortlistingFactor(factor="Location", impact="neutral", reason="Location is not a direct match, but relocation is open.")
    return -8, ShortlistingFactor(factor="Location", impact="negative", reason="JD location does not match candidate location/preferences.")


def _extract_locations(text: str) -> list[str]:
    known = ["mumbai", "navi mumbai", "pune", "bangalore", "bengaluru", "hyderabad", "delhi", "noida", "gurgaon", "remote"]
    lowered = text.lower()
    return [location for location in known if location in lowered]


def _work_mode_factor(request: AnalyzeRequest) -> tuple[int, ShortlistingFactor]:
    context = request.candidateContext
    jd = request.jobDescriptionText.lower()
    modes = ["remote", "hybrid", "onsite", "work from office", "wfo"]
    jd_modes = [mode for mode in modes if mode in jd]
    preferences = " ".join(context.workModePreference).lower()
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
