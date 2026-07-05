from urllib.parse import urlparse

from app.models.analysis import AnalysisResponse, AnalyzeRequest, ResearchBuildRequest, ResearchContextSource, ResearchNoteDraft, RequirementMatch
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
