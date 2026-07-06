from app.models.analysis import ApplicationDecisionRequest, ApplicationDecisionResponse, ApplicationExecutionStep, RequirementMatch


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
        executionPlan=_execution_plan(request, decision, weak_high, missing_high, research_signals, blockers),
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


def _execution_plan(
    request: ApplicationDecisionRequest,
    decision: str,
    weak_high: list[RequirementMatch],
    missing_high: list[RequirementMatch],
    research_signals: list[str],
    blockers: list[str],
) -> list[ApplicationExecutionStep]:
    steps: list[ApplicationExecutionStep] = []
    has_research = bool(research_signals)
    has_blocking_gap = bool(missing_high)

    if not has_research:
        steps.append(
            ApplicationExecutionStep(
                id="research-note",
                label="Add company or role research note",
                actionType="research",
                priority="high" if decision != "skip" else "medium",
                status="ready",
                reason="Decision confidence is limited without company, role, or interview research memory.",
                endpoint="/ai/research/note-draft",
                estimatedUnits=1,
            )
        )

    if weak_high:
        top_gap = weak_high[0]
        steps.append(
            ApplicationExecutionStep(
                id="preparation-plan",
                label=f"Prepare proof for {top_gap.requirement}",
                actionType="prepare",
                priority="critical" if has_blocking_gap else "high",
                status="ready",
                reason=f"{len(weak_high)} high-importance requirement(s) are below the confidence threshold.",
                endpoint="/ai/preparation/plan",
                dependsOn=["research-note"] if not has_research else [],
                estimatedUnits=2,
            )
        )
        steps.append(
            ApplicationExecutionStep(
                id="resume-rewrite",
                label="Review resume wording for weak evidence",
                actionType="rewrite_resume",
                priority="high" if has_blocking_gap else "medium",
                status="ready",
                reason="Evidence-safe rewrite can improve how existing proof is presented, while unsupported gaps stay blocked.",
                endpoint="/ai/resume/rewrite",
                estimatedUnits=2,
            )
        )

    if decision in {"apply", "selective_apply"}:
        steps.append(
            ApplicationExecutionStep(
                id="apply",
                label="Apply and save opportunity status",
                actionType="apply",
                priority="critical" if decision == "apply" else "high",
                status="ready" if not blockers else "blocked",
                reason="The score is strong enough for an application path." if not blockers else "Clear blockers before applying or apply selectively with risk accepted.",
                endpoint="/history/opportunities",
                dependsOn=_apply_dependencies(has_research, weak_high, blockers),
                estimatedUnits=0,
            )
        )
        steps.append(
            ApplicationExecutionStep(
                id="track-opportunity",
                label="Track follow-up in application pipeline",
                actionType="track_opportunity",
                priority="medium",
                status="ready",
                reason="Pipeline tracking preserves the apply decision and next follow-up state for the workspace.",
                endpoint="/history/opportunities",
                dependsOn=["apply"],
                estimatedUnits=0,
            )
        )
    elif decision == "prepare_first":
        steps.append(
            ApplicationExecutionStep(
                id="review-after-prep",
                label="Recheck decision after preparation",
                actionType="review",
                priority="medium",
                status="blocked" if weak_high else "ready",
                reason="Application should wait until the highest-risk gaps are prepared or marked acceptable.",
                endpoint="/ai/application-decision",
                dependsOn=["preparation-plan"] if weak_high else [],
                estimatedUnits=1,
            )
        )
    else:
        steps.append(
            ApplicationExecutionStep(
                id="skip",
                label="Skip and use this JD as a benchmark",
                actionType="skip",
                priority="high",
                status="ready",
                reason="Current score and blockers make this role a poor immediate application target.",
                endpoint="/history/opportunities",
                estimatedUnits=0,
            )
        )

    return steps[:6]


def _apply_dependencies(has_research: bool, weak_high: list[RequirementMatch], blockers: list[str]) -> list[str]:
    dependencies = []
    if not has_research:
        dependencies.append("research-note")
    if weak_high and blockers:
        dependencies.append("preparation-plan")
    return dependencies


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
