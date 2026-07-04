from app.models.analysis import ApplicationDecisionRequest, ApplicationDecisionResponse, RequirementMatch


def build_application_decision(request: ApplicationDecisionRequest) -> ApplicationDecisionResponse:
    analysis = request.analysis
    technical = analysis.technicalMatchScore
    opportunity = analysis.overallOpportunityScore
    shortlisting = analysis.shortlistingScore
    readiness = analysis.interviewReadinessScore
    weak_high = _weak_high_requirements(analysis.requirementMatches)
    missing_high = [match for match in weak_high if match.score < 35]
    research_signals = _research_signals(request)
    blockers = _blockers(missing_high, shortlisting, readiness, research_signals)
    decision = _decision(technical, opportunity, shortlisting, readiness, len(missing_high), len(blockers), bool(research_signals))
    confidence = _confidence(analysis.requirementMatches, request.researchNotes)
    headline = _headline(decision, request.roleTitle or request.sourceRequest.candidateContext.targetRole, request.company)

    return ApplicationDecisionResponse(
        decision=decision,
        confidence=confidence,
        headline=headline,
        reasoning=_reasoning(analysis, weak_high, research_signals),
        blockers=blockers,
        nextActions=_next_actions(decision, weak_high, research_signals),
        researchSignalsUsed=research_signals[:10],
        scoreSignals={
            "technicalMatchScore": technical,
            "overallOpportunityScore": opportunity,
            "shortlistingScore": shortlisting,
            "interviewReadinessScore": readiness,
        },
    )


def _decision(
    technical: int,
    opportunity: int | None,
    shortlisting: int | None,
    readiness: int | None,
    missing_high_count: int,
    blocker_count: int,
    has_research: bool,
) -> str:
    effective_opportunity = opportunity if opportunity is not None else technical
    effective_shortlisting = shortlisting if shortlisting is not None else technical
    effective_readiness = readiness if readiness is not None else technical
    if technical >= 78 and effective_opportunity >= 72 and missing_high_count == 0:
        return "apply"
    if technical >= 68 and blocker_count <= 1:
        return "selective_apply" if has_research else "prepare_first"
    if technical >= 55 or effective_shortlisting >= 65:
        return "prepare_first"
    if effective_readiness < 45 and missing_high_count >= 2:
        return "skip"
    return "prepare_first"


def _confidence(matches: list[RequirementMatch], research_notes) -> str:
    evidence_count = sum(1 for match in matches if match.bestEvidence)
    if evidence_count >= 5 and research_notes:
        return "high"
    if evidence_count >= 3 or research_notes:
        return "medium"
    return "low"


def _headline(decision: str, role_title: str, company: str | None) -> str:
    target = f"{role_title} at {company}" if company else role_title
    labels = {
        "apply": "Apply now",
        "selective_apply": "Apply selectively",
        "prepare_first": "Prepare first",
        "skip": "Skip for now",
    }
    return f"{labels[decision]} for {target}."


def _reasoning(analysis, weak_high: list[RequirementMatch], research_signals: list[str]) -> list[str]:
    reasons = [
        f"Technical match is {analysis.technicalMatchScore}%.",
    ]
    if analysis.overallOpportunityScore is not None:
        reasons.append(f"Overall opportunity score is {analysis.overallOpportunityScore}%.")
    if analysis.shortlistingScore is not None:
        reasons.append(f"Shortlisting score is {analysis.shortlistingScore}%.")
    if weak_high:
        reasons.append(f"{len(weak_high)} high-importance requirement(s) need stronger proof.")
    if research_signals:
        reasons.append(f"{len(research_signals)} saved research signal(s) were considered.")
    if analysis.recommendedAction:
        reasons.append(analysis.recommendedAction)
    return reasons[:8]


def _blockers(
    missing_high: list[RequirementMatch],
    shortlisting: int | None,
    readiness: int | None,
    research_signals: list[str],
) -> list[str]:
    blockers = [f"High-importance missing/weak requirement: {match.requirement}" for match in missing_high[:5]]
    if shortlisting is not None and shortlisting < 50:
        blockers.append("Shortlisting score is below 50%.")
    if readiness is not None and readiness < 50:
        blockers.append("Interview readiness is below 50%.")
    if not research_signals:
        blockers.append("No company or role research note is attached yet.")
    return blockers[:8]


def _next_actions(decision: str, weak_high: list[RequirementMatch], research_signals: list[str]) -> list[str]:
    actions: list[str] = []
    if decision in {"apply", "selective_apply"}:
        actions.append("Apply with the current resume, then track this opportunity in the pipeline.")
    if weak_high:
        actions.append(f"Prepare proof for: {weak_high[0].requirement}.")
    if not research_signals:
        actions.append("Add one research note from the JD, extension handoff, or company page.")
    actions.append("Generate or refresh the preparation plan with saved research notes included.")
    if decision == "skip":
        actions.append("Use this JD as a benchmark and collect similar roles with better fit.")
    return actions[:6]


def _weak_high_requirements(matches: list[RequirementMatch]) -> list[RequirementMatch]:
    return [
        match
        for match in sorted(matches, key=lambda item: item.score)
        if match.importance == "high" and match.score < 65
    ]


def _research_signals(request: ApplicationDecisionRequest) -> list[str]:
    signals: list[str] = []
    for note in request.researchNotes:
        signals.extend(note.keySignals[:4])
        signals.extend([f"Preparation topic: {topic}" for topic in note.preparationTopics[:4]])
    deduped: list[str] = []
    seen: set[str] = set()
    for signal in signals:
        cleaned = signal.strip()
        if not cleaned or cleaned.lower() in seen:
            continue
        seen.add(cleaned.lower())
        deduped.append(cleaned)
    return deduped
