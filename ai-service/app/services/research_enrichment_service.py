from dataclasses import dataclass, field
import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.parse import urlencode
from urllib.request import Request, urlopen

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
    search_url = "https://www.googleapis.com/customsearch/v1"

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

        search_sources: list[ResearchContextSource] = []
        search_key_signals: list[str] = []
        search_topics: list[str] = []
        weak_requirements = [match.requirement for match in analysis.requirementMatches if match.score < 60][:5]
        for query in result.queries[:4]:
            try:
                response = self._search(
                    query=query,
                    api_key=settings.google_api_key,
                    engine_id=settings.google_search_engine_id,
                )
            except ResearchSearchError as exc:
                result.warnings.append(f"Google search failed for '{query}': {exc}")
                continue

            for item in response[:2]:
                source = _assess_source(
                    title=item.title,
                    url=item.url,
                    sourceType=_source_type_for_query(query, research_type),
                    note=f"Google Custom Search result for query: {query}. {item.snippet}",
                )
                search_sources.append(source)
                search_key_signals.append(f"Live source found for {source.sourceType}: {item.title}.")
                search_key_signals.extend(_snippet_signals(item, source.sourceType))
                search_topics.extend(_snippet_topics(item, weak_requirements))

        verified_sources = _dedupe_sources(search_sources)
        if verified_sources:
            planned_sources = [source for source in result.sources if source.citationQuality != "weak"]
            result.sources = [*verified_sources, *planned_sources][:10]
            result.preparation_topics = _dedupe([*search_topics, *result.preparation_topics])[:12]
            result.key_signals = _dedupe([
                f"Google research provider returned {len(verified_sources)} cited source(s).",
                *search_key_signals,
                *result.key_signals,
            ])[:12]
            result.warnings.append("Google provider used live Custom Search results; review citations before relying on them.")
        else:
            result.warnings.append("Google provider returned no usable cited sources; local query-plan sources were kept.")
        return result

    def _search(self, query: str, api_key: str, engine_id: str) -> list["GoogleSearchItem"]:
        params = urlencode({
            "key": api_key,
            "cx": engine_id,
            "q": query,
            "num": 3,
        })
        request = Request(
            f"{self.search_url}?{params}",
            headers={"User-Agent": "career-agent-os-research/0.1"},
        )
        try:
            with urlopen(request, timeout=12) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise ResearchSearchError(f"HTTP {exc.code}") from exc
        except (OSError, URLError, json.JSONDecodeError) as exc:
            raise ResearchSearchError(str(exc)) from exc

        items = payload.get("items", [])
        if not isinstance(items, list):
            return []
        parsed: list[GoogleSearchItem] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            url = str(item.get("link") or "").strip()
            snippet = str(item.get("snippet") or "").strip()
            if title and url:
                parsed.append(GoogleSearchItem(title=title[:220], url=url, snippet=snippet[:500]))
        return parsed


@dataclass
class GoogleSearchItem:
    title: str
    url: str
    snippet: str = ""


class ResearchSearchError(Exception):
    pass


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
    text = query.lower()
    if "interview" in text:
        return "interview_experience"
    if "trend" in text or "market" in text:
        return "market_signal"
    if "job" in text or "requirements" in text:
        return "job_post"
    if "company" in text or "engineering blog" in text or "careers" in text:
        return "company_page"
    research_text = research_type.lower()
    if "interview" in research_text:
        return "interview_experience"
    if "market" in research_text:
        return "market_signal"
    if "company" in research_text:
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


def _dedupe_sources(items: list[ResearchContextSource]) -> list[ResearchContextSource]:
    seen: set[str] = set()
    output: list[ResearchContextSource] = []
    for item in items:
        key = (item.url or item.title).strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


def _snippet_signals(item: GoogleSearchItem, source_type: str) -> list[str]:
    snippet = _clean_snippet(item.snippet)
    if not snippet:
        return []
    return [f"Cited {source_type} source highlights: {snippet[:220]}"]


def _snippet_topics(item: GoogleSearchItem, weak_requirements: list[str]) -> list[str]:
    text = f"{item.title}. {item.snippet}"
    topics: list[str] = []
    lowered = text.lower()
    for requirement in weak_requirements:
        requirement_tokens = _topic_tokens(requirement)
        if requirement_tokens and any(token in lowered for token in requirement_tokens):
            topics.append(requirement)

    topic_rules = [
        ("AI guardrail design", ["guardrail", "permission", "policy", "rollback", "safety"]),
        ("Agent tool permission design", ["agent", "tool permission", "tool permissions"]),
        ("ETL reliability", ["etl", "pipeline", "data quality", "validation"]),
        ("Django API design", ["django", "api", "apis"]),
        ("React UI implementation", ["react", "frontend", "ui"]),
        ("Cloud deployment basics", ["azure", "aws", "gcp", "cloud"]),
        ("SQL performance and validation", ["sql", "database", "query"]),
        ("System design tradeoffs", ["system design", "scalability", "architecture"]),
    ]
    for topic, markers in topic_rules:
        if any(marker in lowered for marker in markers):
            topics.append(topic)

    quoted_phrases = re.findall(r"['\"]([^'\"]{4,80})['\"]", text)
    topics.extend(phrase.strip() for phrase in quoted_phrases[:3])
    return _dedupe(topics)[:8]


def _topic_tokens(value: str) -> list[str]:
    stop_words = {"and", "or", "the", "with", "for", "in", "on", "of", "to", "a", "an"}
    tokens = []
    for token in re.findall(r"[a-z0-9+#.]+", value.lower()):
        if token in stop_words or len(token) < 3:
            continue
        tokens.append(token.rstrip("s"))
    return tokens


def _clean_snippet(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned.strip(" -")
