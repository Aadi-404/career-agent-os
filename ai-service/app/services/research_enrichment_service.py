from dataclasses import dataclass, field
from urllib.parse import urlparse

from app.core.config import get_settings
from app.models.analysis import AnalyzeRequest, AnalysisResponse, ResearchContextSource


@dataclass
class ResearchEnrichmentResult:
    provider: str
    queries: list[str] = field(default_factory=list)
    company_signals: list[str] = field(default_factory=list)
    interview_signals: list[str] = field(default_factory=list)
    market_signals: list[str] = field(default_factory=list)
    key_signals: list[str] = field(default_factory=list)
    preparation_topics: list[str] = field(default_factory=list)
    sources: list[ResearchContextSource] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class ResearchEnrichmentProvider:
    name = "base"

    def enrich(
        self,
        source_request: AnalyzeRequest,
        analysis: AnalysisResponse,
        company: str | None,
        role_title: str,
        research_type: str,
        manual_context: str | None,
    ) -> ResearchEnrichmentResult:
        raise NotImplementedError


class LocalResearchEnrichmentProvider(ResearchEnrichmentProvider):
    name = "local"

    def enrich(
        self,
        source_request: AnalyzeRequest,
        analysis: AnalysisResponse,
        company: str | None,
        role_title: str,
        research_type: str,
        manual_context: str | None,
    ) -> ResearchEnrichmentResult:
        weak_requirements = [match.requirement for match in analysis.requirementMatches if match.score < 60][:5]
        market = source_request.candidateContext.targetMarket or "target job market"
        company_prefix = f"{company} " if company else ""
        company_label = company or "target company"
        company_queries = _dedupe([
            f"{company_prefix}{role_title} company engineering blog",
            f"{company_prefix}{role_title} company careers requirements",
        ])
        interview_queries = _dedupe([
            f"{company_prefix}{role_title} interview experience",
            *[f"{company_prefix}{role_title} {requirement} interview questions" for requirement in weak_requirements[:3]],
        ])
        market_queries = _dedupe([
            f"{role_title} {market} hiring trend",
            f"{role_title} {market} similar job postings requirements",
        ])
        queries = _dedupe([
            *company_queries,
            *interview_queries,
            *market_queries,
        ])[:8]
        company_signals = _dedupe([
            f"Research {company_label} careers pages and engineering content for repeated {role_title} expectations.",
            f"Compare {company_label} role wording against the strongest and weakest resume evidence.",
        ])
        interview_signals = _dedupe([
            f"Search recent {company_prefix}{role_title} interview experiences for rounds, depth, and cross-questions.",
            *[f"Prepare proof and follow-up answers for weak requirement: {requirement}." for requirement in weak_requirements[:3]],
        ])
        market_signals = _dedupe([
            f"Check demand and repeated requirements for {role_title} in {market}.",
            f"Track similar job postings for emphasis on: {', '.join(weak_requirements[:3]) or 'core stack depth'}.",
        ])
        key_signals = _dedupe([
            f"Research provider local prepared {len(queries)} source-search query plan(s).",
            *[f"Company signal: {signal}" for signal in company_signals[:2]],
            *[f"Interview signal: {signal}" for signal in interview_signals[:4]],
            *[f"Market signal: {signal}" for signal in market_signals[:2]],
            *[f"Needs cited research for weak requirement: {requirement}." for requirement in weak_requirements[:4]],
        ])
        preparation_topics = _dedupe([
            *weak_requirements,
            *[item.skill for item in analysis.missingSkills[:3]],
            *[item.skill for item in analysis.weaklyEvidencedSkills[:3]],
        ])[:10]
        sources = [
            _assess_source(
                title=f"Planned search: {query}",
                sourceType=_source_type_for_query(query, research_type),
                note="Local enrichment query plan. Replace with live search result when a web provider is enabled.",
            )
            for query in queries[:6]
        ]
        return ResearchEnrichmentResult(
            provider=self.name,
            queries=queries,
            company_signals=company_signals,
            interview_signals=interview_signals,
            market_signals=market_signals,
            key_signals=key_signals,
            preparation_topics=preparation_topics,
            sources=sources,
            warnings=["Local provider creates citation-ready search plans but does not browse live web sources."],
        )


class GoogleResearchEnrichmentProvider(LocalResearchEnrichmentProvider):
    name = "google"

    def enrich(
        self,
        source_request: AnalyzeRequest,
        analysis: AnalysisResponse,
        company: str | None,
        role_title: str,
        research_type: str,
        manual_context: str | None,
    ) -> ResearchEnrichmentResult:
        settings = get_settings()
        result = super().enrich(source_request, analysis, company, role_title, research_type, manual_context)
        result.provider = self.name
        if not settings.google_api_key or not settings.google_search_engine_id:
            result.warnings.append("Google research provider is configured but missing GOOGLE_API_KEY or GOOGLE_SEARCH_ENGINE_ID.")
            return result
        result.warnings.append("Google provider interface is ready; live HTTP search execution is intentionally disabled in local builds.")
        return result


def build_research_enrichment(
    source_request: AnalyzeRequest,
    analysis: AnalysisResponse,
    company: str | None,
    role_title: str,
    research_type: str,
    manual_context: str | None = None,
) -> ResearchEnrichmentResult:
    settings = get_settings()
    provider: ResearchEnrichmentProvider
    if settings.research_provider == "google":
        provider = GoogleResearchEnrichmentProvider()
    else:
        provider = LocalResearchEnrichmentProvider()
    return provider.enrich(source_request, analysis, company, role_title, research_type, manual_context)


def _source_type_for_query(query: str, research_type: str) -> str:
    text = f"{query} {research_type}".lower()
    if "interview" in text:
        return "interview_experience"
    if "trend" in text or "market" in text:
        return "market_signal"
    if "job" in text or "requirements" in text:
        return "job_post"
    if "company" in text or "engineering blog" in text or "careers" in text:
        return "company_page"
    return "other"


def _assess_source(
    title: str,
    url: str | None = None,
    sourceType: str = "manual",
    note: str | None = None,
) -> ResearchContextSource:
    cleaned_url = url.strip() if url else None
    issues: list[str] = []
    quality = "uncited"
    if cleaned_url:
        parsed = urlparse(cleaned_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            issues.append("URL is not a valid http(s) citation.")
            quality = "weak"
        else:
            quality = "verified_url"
    elif sourceType == "manual":
        quality = "manual_note"
        if not note:
            issues.append("Manual source should include a note explaining provenance.")
    else:
        quality = "weak"
        issues.append("Non-manual source is missing a URL citation.")
    return ResearchContextSource(
        title=title,
        url=cleaned_url,
        sourceType=sourceType,
        note=note,
        citationQuality=quality,
        validationIssues=issues,
    )


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        cleaned = item.strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        output.append(cleaned)
    return output
