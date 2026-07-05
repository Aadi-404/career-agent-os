from dataclasses import dataclass, field
from html.parser import HTMLParser
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
    market_opportunity_signals: list[str] = field(default_factory=list)
    role_company_synthesis: list[str] = field(default_factory=list)
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
        market_opportunity_signals = _dedupe([
            f"Market opportunity needs cited validation for {role_title} in {market}.",
            f"Compare repeated job-post requirements against candidate gaps: {', '.join(weak_requirements[:3]) or 'no major weak requirement'}.",
        ])
        role_company_synthesis = _dedupe([
            f"Synthesize {company_label} expectations with the JD match matrix before preparing.",
            f"Prioritize proof stories for weak requirements that appear in company, interview, or market sources.",
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
            market_opportunity_signals=market_opportunity_signals,
            role_company_synthesis=role_company_synthesis,
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
        page_extracts: list[PageExtract] = []
        evidence_documents: list[EvidenceDocument] = []
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
                evidence_documents.append(
                    EvidenceDocument(
                        source_type=source.sourceType,
                        title=item.title,
                        text=f"{item.title}. {item.snippet}",
                    )
                )
                try:
                    page_extract = self._extract_page(item.url)
                    page_extracts.append(page_extract)
                    source.note = _source_note_with_page_extract(source.note, page_extract)
                    search_key_signals.extend(_page_signals(page_extract, source.sourceType))
                    search_topics.extend(_page_topics(page_extract, weak_requirements))
                    evidence_documents.append(
                        EvidenceDocument(
                            source_type=source.sourceType,
                            title=item.title,
                            text=page_extract.text,
                        )
                    )
                except ResearchSearchError as exc:
                    result.warnings.append(f"Page extraction skipped for '{item.title}': {exc}")

        verified_sources = _dedupe_sources(search_sources)
        if verified_sources:
            planned_sources = [source for source in result.sources if source.citationQuality != "weak"]
            result.sources = [*verified_sources, *planned_sources][:10]
            result.preparation_topics = _dedupe([*search_topics, *result.preparation_topics])[:12]
            result.market_opportunity_signals = _dedupe([
                *_market_opportunity_signals(role_title, source_request.candidateContext.targetMarket, evidence_documents),
                *result.market_opportunity_signals,
            ])[:8]
            result.role_company_synthesis = _dedupe([
                *_role_company_synthesis(company, role_title, weak_requirements, evidence_documents),
                *result.role_company_synthesis,
            ])[:8]
            result.key_signals = _dedupe([
                f"Google research provider returned {len(verified_sources)} cited source(s).",
                *([f"Extracted readable text from {len(page_extracts)} cited page(s)."] if page_extracts else []),
                *[f"Market opportunity: {signal}" for signal in result.market_opportunity_signals[:3]],
                *[f"Role/company synthesis: {signal}" for signal in result.role_company_synthesis[:3]],
                *search_key_signals,
                *result.key_signals,
            ])[:12]
            result.warnings.append("Google provider used live Custom Search results; review citations before relying on them.")
        else:
            result.warnings.append("Google provider returned no usable cited sources; local query-plan sources were kept.")
        return result

    def _extract_page(self, url: str) -> "PageExtract":
        parsed_url = urlparse(url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise ResearchSearchError("invalid page URL")
        request = Request(
            url,
            headers={"User-Agent": "career-agent-os-research/0.1"},
        )
        try:
            with urlopen(request, timeout=8) as response:
                content_type = response.headers.get("content-type", "")
                if "text/html" not in content_type and "text/plain" not in content_type:
                    raise ResearchSearchError(f"unsupported content type {content_type or 'unknown'}")
                raw = response.read(180_000)
        except HTTPError as exc:
            raise ResearchSearchError(f"HTTP {exc.code}") from exc
        except (OSError, URLError) as exc:
            raise ResearchSearchError(str(exc)) from exc

        text = raw.decode("utf-8", errors="ignore")
        if "html" in content_type:
            text = _html_to_text(text)
        cleaned = _clean_snippet(text)
        if len(cleaned) < 80:
            raise ResearchSearchError("page returned too little readable text")
        return PageExtract(url=url, text=cleaned[:2500])

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


@dataclass
class PageExtract:
    url: str
    text: str


@dataclass
class EvidenceDocument:
    source_type: str
    title: str
    text: str


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


def _page_signals(extract: PageExtract, source_type: str) -> list[str]:
    summary = _first_relevant_sentence(extract.text)
    if not summary:
        return []
    return [f"Extracted {source_type} page evidence: {summary[:220]}"]


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


def _page_topics(extract: PageExtract, weak_requirements: list[str]) -> list[str]:
    return _snippet_topics(GoogleSearchItem(title="Extracted page", url=extract.url, snippet=extract.text), weak_requirements)


def _market_opportunity_signals(role_title: str, market: str, documents: list[EvidenceDocument]) -> list[str]:
    if not documents:
        return []
    source_counts = _source_type_counts(documents)
    repeated_terms = _repeated_market_terms(documents)
    signals = [
        f"{len(documents)} cited evidence fragment(s) were reviewed for {role_title} in {market}.",
    ]
    job_post_count = source_counts.get("job_post", 0)
    market_count = source_counts.get("market_signal", 0)
    interview_count = source_counts.get("interview_experience", 0)
    company_count = source_counts.get("company_page", 0)
    if job_post_count:
        signals.append(f"{job_post_count} job-post source(s) indicate demand or repeated hiring requirements.")
    if market_count:
        signals.append(f"{market_count} market source(s) indicate role-demand or trend evidence.")
    if interview_count:
        signals.append(f"{interview_count} interview source(s) show candidate-screening pressure for this role.")
    if company_count:
        signals.append(f"{company_count} company source(s) show employer-specific expectations.")
    if repeated_terms:
        signals.append(f"Repeated cited market emphasis: {', '.join(repeated_terms[:5])}.")
    return _dedupe(signals)


def _role_company_synthesis(
    company: str | None,
    role_title: str,
    weak_requirements: list[str],
    documents: list[EvidenceDocument],
) -> list[str]:
    if not documents:
        return []
    target = f"{role_title} at {company}" if company else role_title
    text = " ".join(document.text.lower() for document in documents)
    repeated_terms = _repeated_market_terms(documents)
    matched_gaps = []
    for requirement in weak_requirements:
        tokens = _topic_tokens(requirement)
        if tokens and any(token in text for token in tokens):
            matched_gaps.append(requirement)
    signals = [f"Cited evidence was synthesized for {target} across {len(documents)} source fragment(s)."]
    if matched_gaps:
        signals.append(f"Candidate weak areas also appear in cited evidence: {', '.join(matched_gaps[:4])}.")
    if repeated_terms:
        signals.append(f"Role/company preparation should emphasize: {', '.join(repeated_terms[:5])}.")
    if not matched_gaps and not repeated_terms:
        signals.append("Cited evidence did not strongly repeat the current weak requirements; keep preparation anchored to the JD matrix.")
    return _dedupe(signals)


def _source_type_counts(documents: list[EvidenceDocument]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for document in documents:
        counts[document.source_type] = counts.get(document.source_type, 0) + 1
    return counts


def _repeated_market_terms(documents: list[EvidenceDocument]) -> list[str]:
    labels = {
        "AI guardrails": ["guardrail", "safety", "policy", "permission"],
        "agent workflows": ["agent", "workflow", "automation"],
        "ETL reliability": ["etl", "pipeline", "data quality", "validation"],
        "Django APIs": ["django", "api", "apis"],
        "React frontend": ["react", "frontend", "ui"],
        "SQL/data validation": ["sql", "database", "query"],
        "cloud basics": ["azure", "aws", "gcp", "cloud"],
        "system design": ["system design", "scalability", "architecture"],
        "Power BI/reporting": ["power bi", "dashboard", "reporting"],
    }
    text = " ".join(document.text.lower() for document in documents)
    repeated = []
    for label, markers in labels.items():
        hits = sum(text.count(marker) for marker in markers)
        if hits >= 2:
            repeated.append((label, hits))
    repeated.sort(key=lambda item: item[1], reverse=True)
    return [label for label, _hits in repeated]


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


def _source_note_with_page_extract(note: str | None, extract: PageExtract) -> str:
    page_signal = _first_relevant_sentence(extract.text) or extract.text[:220]
    return f"{note or ''} Extracted page text: {page_signal[:320]}".strip()


def _first_relevant_sentence(text: str) -> str:
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        cleaned = sentence.strip()
        if 45 <= len(cleaned) <= 260:
            return cleaned
    return text[:220].strip()


def _html_to_text(value: str) -> str:
    parser = _ResearchHtmlTextParser()
    parser.feed(value)
    parser.close()
    return parser.text()


class _ResearchHtmlTextParser(HTMLParser):
    ignored_tags = {"script", "style", "noscript", "svg", "canvas", "template"}

    def __init__(self) -> None:
        super().__init__()
        self._ignored_depth = 0
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in self.ignored_tags:
            self._ignored_depth += 1
        if tag in {"p", "li", "br", "h1", "h2", "h3", "h4", "section", "article", "div"}:
            self._chunks.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.ignored_tags and self._ignored_depth:
            self._ignored_depth -= 1
        if tag in {"p", "li", "h1", "h2", "h3", "h4", "section", "article", "div"}:
            self._chunks.append(" ")

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        cleaned = data.strip()
        if cleaned:
            self._chunks.append(cleaned)

    def text(self) -> str:
        return " ".join(self._chunks)
