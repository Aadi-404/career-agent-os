from collections import Counter, defaultdict

from app.models.history import (
    AnalysisRecord,
    JobDescriptionRecord,
    JobOpportunityRecord,
    PreparationSessionRecord,
    ResearchNoteRecord,
    ResumeRecord,
)
from app.models.workspace_memory import WorkspaceMemoryGap, WorkspaceMemoryItem, WorkspaceMemoryResponse


def build_workspace_memory(
    user_id: str,
    resumes: list[ResumeRecord],
    job_descriptions: list[JobDescriptionRecord],
    analyses: list[AnalysisRecord],
    research_notes: list[ResearchNoteRecord],
    preparation_sessions: list[PreparationSessionRecord],
    opportunities: list[JobOpportunityRecord],
) -> WorkspaceMemoryResponse:
    evidence = _top_evidence(resumes, job_descriptions, analyses, research_notes, opportunities)
    gaps = _recurring_gaps(analyses)
    research_signals = _research_signals(research_notes)
    preparation_signals = _preparation_signals(preparation_sessions)
    retrieval_queries = _retrieval_queries(gaps, research_notes, analyses)
    memory_score = _memory_score(evidence, gaps, research_notes, preparation_sessions, opportunities)
    next_actions = _next_actions(evidence, gaps, research_notes, preparation_sessions, opportunities)
    total_items = len(resumes) + len(job_descriptions) + len(analyses) + len(research_notes) + len(preparation_sessions) + len(opportunities)
    return WorkspaceMemoryResponse(
        userId=user_id,
        summary=_summary(total_items, memory_score, gaps, research_notes, preparation_sessions),
        memoryScore=memory_score,
        totalItems=total_items,
        topEvidence=evidence[:10],
        recurringGaps=gaps[:8],
        researchSignals=research_signals[:10],
        preparationSignals=preparation_signals[:10],
        retrievalQueries=retrieval_queries[:10],
        nextActions=next_actions[:6],
    )


def _top_evidence(
    resumes: list[ResumeRecord],
    job_descriptions: list[JobDescriptionRecord],
    analyses: list[AnalysisRecord],
    research_notes: list[ResearchNoteRecord],
    opportunities: list[JobOpportunityRecord],
) -> list[WorkspaceMemoryItem]:
    items: list[WorkspaceMemoryItem] = []
    for analysis in analyses[:10]:
        strong = [match for match in analysis.response.requirementMatches if match.score >= 70 and match.bestEvidence]
        summary = "; ".join(f"{match.requirement}: {match.bestEvidence}" for match in strong[:3])
        if not summary:
            summary = analysis.response.overallSummary
        items.append(
            WorkspaceMemoryItem(
                id=analysis.id,
                sourceType="analysis",
                title=analysis.title,
                summary=summary[:700],
                tags=_dedupe([analysis.fitCategory, *(match.category for match in strong[:4])]),
                score=max(0, min(100, analysis.technicalMatchScore)),
                createdAt=analysis.createdAt,
            )
        )
    for note in research_notes[:8]:
        items.append(
            WorkspaceMemoryItem(
                id=note.id,
                sourceType="research",
                title=note.title,
                summary=note.summary[:700],
                tags=_dedupe([note.researchType, *(note.preparationTopics[:4])]),
                score=_research_item_score(note),
                createdAt=note.createdAt,
            )
        )
    for opportunity in opportunities[:8]:
        items.append(
            WorkspaceMemoryItem(
                id=opportunity.id,
                sourceType="opportunity",
                title=opportunity.company and f"{opportunity.title} at {opportunity.company}" or opportunity.title,
                summary=(opportunity.analysisResponse.overallSummary if opportunity.analysisResponse else opportunity.description)[:700],
                tags=_dedupe([opportunity.status, opportunity.fitCategory or "", str(opportunity.technicalMatchScore or "")]),
                score=opportunity.technicalMatchScore or 35,
                createdAt=opportunity.createdAt,
            )
        )
    for resume in resumes[:4]:
        items.append(
            WorkspaceMemoryItem(
                id=resume.id,
                sourceType="resume",
                title=resume.title,
                summary=(resume.normalizedText or resume.rawText)[:700],
                tags=["resume", resume.source],
                score=55 if resume.structuredResume else 40,
                createdAt=resume.updatedAt,
            )
        )
    for jd in job_descriptions[:4]:
        items.append(
            WorkspaceMemoryItem(
                id=jd.id,
                sourceType="jd",
                title=jd.company and f"{jd.title} at {jd.company}" or jd.title,
                summary=(jd.normalizedText or jd.rawText)[:700],
                tags=["job_description", *(jd.parsedJobDescription.requiredSkills[:4] if jd.parsedJobDescription else [])],
                score=50,
                createdAt=jd.updatedAt,
            )
        )
    return sorted(items, key=lambda item: (-item.score, item.sourceType, item.title))


def _recurring_gaps(analyses: list[AnalysisRecord]) -> list[WorkspaceMemoryGap]:
    grouped: dict[str, list[str | None]] = defaultdict(list)
    for analysis in analyses:
        for match in analysis.response.requirementMatches:
            if match.score >= 60:
                continue
            grouped[_topic_key(match.requirement)].append(match.bestEvidence or match.reason)
    gaps = [
        WorkspaceMemoryGap(
            topic=topic,
            occurrences=len(evidence),
            latestEvidence=next((item for item in evidence if item), None),
            recommendation=_gap_recommendation(topic, len(evidence)),
        )
        for topic, evidence in grouped.items()
    ]
    return sorted(gaps, key=lambda item: (-item.occurrences, item.topic))


def _research_signals(notes: list[ResearchNoteRecord]) -> list[str]:
    signals = []
    for note in notes[:8]:
        prefix = f"{note.company or note.roleTitle or note.researchType}:"
        signals.extend(f"{prefix} {signal}" for signal in note.keySignals[:3])
        signals.extend(f"{prefix} prepare {topic}" for topic in note.preparationTopics[:2])
    return _dedupe(signals)


def _preparation_signals(sessions: list[PreparationSessionRecord]) -> list[str]:
    signals = []
    for session in sessions[:8]:
        progress = session.progress or {}
        tasks = progress.get("tasks", {}) if isinstance(progress, dict) else {}
        confidence = progress.get("confidence", {}) if isinstance(progress, dict) else {}
        done = sum(1 for value in tasks.values() if value in {"done", "skipped"}) if isinstance(tasks, dict) else 0
        total = len(tasks) if isinstance(tasks, dict) else 0
        low = sum(1 for value in confidence.values() if value == "low") if isinstance(confidence, dict) else 0
        signals.append(f"{session.title}: {done}/{total} tracked task(s), {low} low-confidence day(s), status {session.status}.")
    return signals


def _retrieval_queries(gaps: list[WorkspaceMemoryGap], notes: list[ResearchNoteRecord], analyses: list[AnalysisRecord]) -> list[str]:
    queries = []
    latest_role = analyses[0].request.candidateContext.targetRole if analyses else None
    for gap in gaps[:5]:
        queries.append(f"Find resume evidence and preparation history for {gap.topic}")
    for note in notes[:4]:
        target = " ".join(item for item in [note.company, note.roleTitle] if item)
        if target:
            queries.append(f"Retrieve research memory for {target}")
    if latest_role:
        queries.append(f"Compare latest {latest_role} score with previous saved analyses")
    return _dedupe(queries)


def _memory_score(
    evidence: list[WorkspaceMemoryItem],
    gaps: list[WorkspaceMemoryGap],
    research_notes: list[ResearchNoteRecord],
    preparation_sessions: list[PreparationSessionRecord],
    opportunities: list[JobOpportunityRecord],
) -> int:
    score = 15
    score += min(25, len(evidence) * 3)
    score += min(20, len(research_notes) * 4)
    score += min(15, len(preparation_sessions) * 3)
    score += min(15, len(opportunities) * 2)
    score -= min(15, len([gap for gap in gaps if gap.occurrences >= 2]) * 3)
    return max(0, min(100, score))


def _next_actions(
    evidence: list[WorkspaceMemoryItem],
    gaps: list[WorkspaceMemoryGap],
    research_notes: list[ResearchNoteRecord],
    preparation_sessions: list[PreparationSessionRecord],
    opportunities: list[JobOpportunityRecord],
) -> list[str]:
    actions = []
    if not evidence:
        actions.append("Run and save at least one score to seed workspace memory.")
    if gaps:
        actions.append(f"Use memory retrieval to prepare the recurring gap: {gaps[0].topic}.")
    if not research_notes:
        actions.append("Save one company or interview research note for the latest target role.")
    if not preparation_sessions:
        actions.append("Generate and save a preparation plan so progress can become memory.")
    if not opportunities:
        actions.append("Save one extension job match to build application pipeline memory.")
    if not actions:
        actions.append("Use the top evidence and retrieval queries when generating the next agent plan.")
    return actions


def _summary(total_items: int, score: int, gaps: list[WorkspaceMemoryGap], notes: list[ResearchNoteRecord], sessions: list[PreparationSessionRecord]) -> str:
    if total_items == 0:
        return "Workspace memory is empty. Save scores, research, preparation, and opportunities to build context."
    return f"Workspace memory has {total_items} saved item(s), score {score}%, {len(gaps)} recurring gap(s), {len(notes)} research note(s), and {len(sessions)} prep session(s)."


def _research_item_score(note: ResearchNoteRecord) -> int:
    verified = len([source for source in note.sources if source.citationQuality == "verified_url"])
    weak = len([source for source in note.sources if source.citationQuality == "weak"])
    return max(25, min(100, 45 + verified * 12 + len(note.keySignals) * 2 - weak * 5))


def _gap_recommendation(topic: str, occurrences: int) -> str:
    if occurrences >= 3:
        return f"Treat {topic} as a repeated blocker; prepare a proof story and update resume evidence if truthful."
    return f"Review saved analyses for {topic} and add research/prep notes before applying to similar JDs."


def _topic_key(value: str) -> str:
    return " ".join(value.strip().split())


def _dedupe(items) -> list[str]:
    output = []
    seen = set()
    for item in items:
        cleaned = str(item).strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        output.append(cleaned)
    return output
