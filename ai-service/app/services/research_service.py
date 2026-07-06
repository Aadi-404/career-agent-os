from urllib.parse import urlparse

from app.models.analysis import (
    AnalysisResponse,
    AnalyzeRequest,
    ResearchBuildRequest,
    ResearchContextSource,
    ResearchNoteDraft,
    ResearchSourceReview,
    ResearchSourceReviewItem,
    RequirementMatch,
)
from app.services.research_enrichment_service import build_research_enrichment


ALLOWED_SOURCE_TYPES = {"manual", "job_post", "interview_experience", "company_page", "market_signal", "other"}


def build_research_note_draft(request: ResearchBuildRequest) -> ResearchNoteDraft:
    source_request = request.sourceRequest
    analysis = request.analysis
    company = _clean_optional(request.company)
    role_title = _clean_optional(request.roleTitle) or source_request.candidateContext.targetRole
    priority_matches = _priority_matches(analysis.requirementMatches)
    weak_matches = [match for match in priority_matches if match.score < 60]
    strong_matches = [match for match in priority_matches if match.score >= 70]
    manual_signals = _manual_signals(request.manualContext)
    enrichment = build_research_enrichment(
        source_request=source_request,
        analysis=analysis,
        company=company,
        role_title=role_title,
        research_type=request.researchType or "role",
        manual_context=request.manualContext,
    )

    key_signals = _dedupe([
        *[f"Company research: {signal}" for signal in enrichment.company_signals[:1]],
        *[f"Interview research: {signal}" for signal in enrichment.interview_signals[:2]],
        *[f"Market research: {signal}" for signal in enrichment.market_signals[:1]],
        *[f"Market opportunity: {signal}" for signal in enrichment.market_opportunity_signals[:1]],
        *[f"Role/company synthesis: {signal}" for signal in enrichment.role_company_synthesis[:1]],
        *_manual_signal_labels(manual_signals),
        *enrichment.key_signals,
        *[f"{match.requirement} is weak or missing in resume evidence." for match in weak_matches[:5]],
        *[f"{match.requirement} is a strong existing proof area." for match in strong_matches[:3]],
        f"Current technical match score is {analysis.technicalMatchScore}% ({analysis.fitCategory}).",
    ])[:18]

    preparation_topics = _dedupe([
        *enrichment.preparation_topics,
        *manual_signals,
        *[match.requirement for match in weak_matches[:6]],
        *[item.skill for item in analysis.missingSkills[:4]],
        *[item.skill for item in analysis.weaklyEvidencedSkills[:4]],
    ])[:12]

    source_labels = _source_labels(request.sourceUrls)
    sources = [
        _assess_source(
            title="Current JD and match analysis",
            sourceType="job_post",
            note=f"Generated from the saved score report for {role_title}.",
        ),
        *source_labels,
        *enrichment.sources,
    ][:10]
    source_review = _review_sources(
        sources=sources,
        company=company,
        role_title=role_title,
        weak_matches=weak_matches,
        provider=enrichment.provider,
    )

    summary = _summary(
        role_title=role_title,
        company=company,
        analysis=analysis,
        weak_matches=weak_matches,
        strong_matches=strong_matches,
        manual_context=request.manualContext,
        enrichment_signal_text=_enrichment_signal_text(enrichment),
    )
    title = f"{company + ' ' if company else ''}{role_title} research signals".strip()
    return ResearchNoteDraft(
        title=title[:180],
        company=company,
        roleTitle=role_title,
        researchType=request.researchType or "role",
        summary=summary,
        keySignals=key_signals,
        preparationTopics=preparation_topics or [role_title],
        sources=sources,
        researchProvider=enrichment.provider,
        providerWarnings=enrichment.warnings,
        marketOpportunitySignals=enrichment.market_opportunity_signals,
        roleCompanySynthesis=enrichment.role_company_synthesis,
        sourceReview=source_review,
    )


def _summary(
    role_title: str,
    company: str | None,
    analysis: AnalysisResponse,
    weak_matches: list[RequirementMatch],
    strong_matches: list[RequirementMatch],
    manual_context: str | None,
    enrichment_signal_text: str,
) -> str:
    company_text = f" at {company}" if company else ""
    weak_text = ", ".join(match.requirement for match in weak_matches[:4]) or "no major weak requirement"
    strong_text = ", ".join(match.requirement for match in strong_matches[:3]) or "general role alignment"
    manual_text = f" Manual context also mentions: {manual_context.strip()[:420]}" if manual_context and manual_context.strip() else ""
    return (
        f"Research draft for {role_title}{company_text}. The current score is {analysis.technicalMatchScore}% "
        f"with fit category {analysis.fitCategory}. Strong proof areas: {strong_text}. "
        f"Preparation should focus on: {weak_text}.{enrichment_signal_text}{manual_text}"
    )


def _enrichment_signal_text(enrichment) -> str:
    total = len(enrichment.company_signals) + len(enrichment.interview_signals) + len(enrichment.market_signals)
    if not total:
        return ""
    return (
        f" Research enrichment separated {len(enrichment.company_signals)} company, "
        f"{len(enrichment.interview_signals)} interview, and {len(enrichment.market_signals)} market signal(s) "
        "for cited follow-up."
    )


def _priority_matches(matches: list[RequirementMatch]) -> list[RequirementMatch]:
    return sorted(matches, key=lambda match: (_importance_rank(match.importance), match.score))


def _importance_rank(importance: str) -> int:
    if importance == "high":
        return 0
    if importance == "medium":
        return 1
    return 2


def _manual_signals(value: str | None) -> list[str]:
    if not value:
        return []
    signals = []
    for line in value.splitlines():
        cleaned = line.strip(" -\t")
        if len(cleaned) >= 3:
            signals.append(cleaned)
    if signals:
        return signals[:8]
    cleaned = value.strip()
    return [cleaned[:180]] if cleaned else []


def _manual_signal_labels(signals: list[str]) -> list[str]:
    return [f"Manual research signal: {signal}" for signal in signals[:5]]


def _source_labels(urls: list[str]) -> list[ResearchContextSource]:
    sources: list[ResearchContextSource] = []
    for index, url in enumerate(urls[:10], start=1):
        cleaned = url.strip()
        if not cleaned:
            continue
        sources.append(
            _assess_source(
                title=f"Research source {index}",
                url=cleaned,
                sourceType=_infer_source_type(cleaned, f"Research source {index}"),
                note="User-provided source URL. Citation quality is validated locally; live extraction is planned for the web research phase.",
            )
        )
    return sources


def assess_research_source(
    title: str,
    url: str | None = None,
    sourceType: str = "manual",
    note: str | None = None,
) -> ResearchContextSource:
    cleaned_url = url.strip() if url else None
    cleaned_type = sourceType if sourceType in ALLOWED_SOURCE_TYPES else "other"
    issues: list[str] = []
    quality = "uncited"
    if cleaned_url:
        parsed = urlparse(cleaned_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            issues.append("URL is not a valid http(s) citation.")
            quality = "weak"
        else:
            quality = "verified_url"
            if cleaned_type == "manual":
                issues.append("Source has a URL but is still marked manual.")
    elif cleaned_type == "manual":
        quality = "manual_note"
        if not note:
            issues.append("Manual source should include a note explaining provenance.")
    else:
        quality = "weak"
        issues.append("Non-manual source is missing a URL citation.")

    return ResearchContextSource(
        title=title,
        url=cleaned_url,
        sourceType=cleaned_type,
        note=note,
        citationQuality=quality,
        validationIssues=issues,
    )


_assess_source = assess_research_source


def _review_sources(
    sources: list[ResearchContextSource],
    company: str | None,
    role_title: str,
    weak_matches: list[RequirementMatch],
    provider: str,
) -> ResearchSourceReview:
    verified = [source for source in sources if source.citationQuality == "verified_url"]
    manual = [source for source in sources if source.citationQuality == "manual_note"]
    weak = [source for source in sources if source.citationQuality == "weak"]
    type_counts: dict[str, int] = {}
    for source in sources:
        type_counts[source.sourceType] = type_counts.get(source.sourceType, 0) + 1
    verified_type_counts: dict[str, int] = {}
    for source in verified:
        verified_type_counts[source.sourceType] = verified_type_counts.get(source.sourceType, 0) + 1

    reviewed = sorted(
        [_review_source_item(source, company, role_title) for source in sources],
        key=lambda item: (-item.credibilityScore, item.title.lower()),
    )
    citation_score = _citation_score(reviewed, sources)
    gaps = _research_gaps(sources, type_counts, verified_type_counts, verified, weak, company, provider)
    searches = _recommended_source_searches(company, role_title, weak_matches, verified_type_counts, gaps)
    return ResearchSourceReview(
        confidence=_research_confidence(citation_score, len(verified), gaps),
        citationScore=citation_score,
        verifiedSourceCount=len(verified),
        manualSourceCount=len(manual),
        weakSourceCount=len(weak),
        sourceTypeCounts=type_counts,
        topSources=reviewed[:5],
        gaps=gaps,
        recommendedSearches=searches,
    )


def _review_source_item(source: ResearchContextSource, company: str | None, role_title: str) -> ResearchSourceReviewItem:
    score = 20
    reasons = []
    if source.citationQuality == "verified_url":
        score += 45
        reasons.append("verified URL")
    elif source.citationQuality == "manual_note":
        score += 25
        reasons.append("manual provenance")
    elif source.citationQuality == "weak":
        score += 5
        reasons.append("weak or missing citation")

    score += {
        "company_page": 15,
        "interview_experience": 14,
        "job_post": 12,
        "market_signal": 10,
        "manual": 6,
        "other": 4,
    }.get(source.sourceType, 4)

    text = f"{source.title} {source.url or ''} {source.note or ''}".lower()
    if company and company.lower() in text:
        score += 8
        reasons.append("company-specific")
    if role_title.lower() in text:
        score += 5
        reasons.append("role-specific")
    if source.note and len(source.note) >= 120:
        score += 5
        reasons.append("has usable evidence note")
    if source.validationIssues:
        score -= min(25, 8 * len(source.validationIssues))
        reasons.append("validation issue")

    return ResearchSourceReviewItem(
        title=source.title,
        url=source.url,
        sourceType=source.sourceType,
        citationQuality=source.citationQuality,
        credibilityScore=max(0, min(100, score)),
        reason=", ".join(reasons) or "source recorded without strong quality signal",
    )


def _citation_score(reviewed: list[ResearchSourceReviewItem], sources: list[ResearchContextSource]) -> int:
    if not sources:
        return 0
    average = round(sum(item.credibilityScore for item in reviewed) / len(sources))
    verified_bonus = min(15, 5 * len([source for source in sources if source.citationQuality == "verified_url"]))
    weak_penalty = min(20, 5 * len([source for source in sources if source.citationQuality == "weak"]))
    return max(0, min(100, average + verified_bonus - weak_penalty))


def _research_confidence(citation_score: int, verified_count: int, gaps: list[str]) -> str:
    if citation_score >= 72 and verified_count >= 3 and len(gaps) <= 1:
        return "high"
    if citation_score >= 45 and verified_count >= 1:
        return "medium"
    return "low"


def _research_gaps(
    sources: list[ResearchContextSource],
    type_counts: dict[str, int],
    verified_type_counts: dict[str, int],
    verified: list[ResearchContextSource],
    weak: list[ResearchContextSource],
    company: str | None,
    provider: str,
) -> list[str]:
    gaps = []
    if not sources:
        gaps.append("No research sources are attached.")
    if not verified:
        gaps.append("No verified URL citation is available yet.")
    if weak:
        gaps.append(f"{len(weak)} source(s) are weak because citations are missing or invalid.")
    if company and verified_type_counts.get("company_page", 0) == 0:
        gaps.append("No verified company-specific source is attached.")
    if verified_type_counts.get("interview_experience", 0) == 0:
        gaps.append("No verified interview-experience source is attached.")
    if verified_type_counts.get("job_post", 0) == 0:
        gaps.append("No verified comparable job-post source is attached.")
    if provider == "local":
        gaps.append("Research is still a local query plan until live sources are added.")
    return gaps[:8]


def _recommended_source_searches(
    company: str | None,
    role_title: str,
    weak_matches: list[RequirementMatch],
    type_counts: dict[str, int],
    gaps: list[str],
) -> list[str]:
    company_prefix = f"{company} " if company else ""
    searches = []
    if any("company-specific" in gap for gap in gaps):
        searches.append(f"{company_prefix}{role_title} careers engineering blog")
    if type_counts.get("interview_experience", 0) == 0:
        searches.append(f"{company_prefix}{role_title} interview experience")
    if type_counts.get("job_post", 0) == 0:
        searches.append(f"{role_title} similar job postings requirements")
    for match in weak_matches[:3]:
        searches.append(f"{company_prefix}{role_title} {match.requirement} interview questions")
    return _dedupe(searches)[:8]


def _infer_source_type(url: str, title: str) -> str:
    text = f"{url} {title}".lower()
    if any(marker in text for marker in ["linkedin", "naukri", "indeed", "jobs", "careers", "greenhouse", "lever.co"]):
        return "job_post"
    if any(marker in text for marker in ["interview", "glassdoor", "ambitionbox", "leetcode discuss"]):
        return "interview_experience"
    if any(marker in text for marker in ["news", "trend", "report", "survey", "market"]):
        return "market_signal"
    return "other"


def _clean_optional(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip()
    return cleaned or None


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        cleaned = item.strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(cleaned)
    return deduped
