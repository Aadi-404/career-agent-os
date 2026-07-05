from app.models.analysis import (
    AgentToolRecommendation,
    CareerAgentPlanRequest,
    CareerAgentPlanResponse,
    RequirementMatch,
)


def build_career_agent_plan(request: CareerAgentPlanRequest) -> CareerAgentPlanResponse:
    analysis = request.analysis
    artifacts = {artifact.strip().lower() for artifact in request.generatedArtifacts if artifact.strip()}
    weak_requirements = _weak_requirements(analysis.requirementMatches)
    missing_requirements = [match for match in weak_requirements if match.score < 20 or match.evidenceSource == "missing"]
    high_risk_requirements = [match for match in weak_requirements if match.importance == "high"]

    recommendations: list[AgentToolRecommendation] = []

    if not request.researchNotes:
        recommendations.append(
            AgentToolRecommendation(
                tool="research_note",
                priority="high" if analysis.technicalMatchScore >= 55 else "medium",
                reason="No saved company or role research note is attached. Research improves preparation and apply/skip decisions.",
                endpoint="/ai/research/note-draft",
                estimatedUnits=1,
                requiresPremium=True,
            )
        )
    else:
        recommendations.append(
            AgentToolRecommendation(
                tool="research_note",
                priority="low",
                reason=f"{len(request.researchNotes)} research note(s) are already available for this opportunity.",
                endpoint="/ai/research/note-draft",
                estimatedUnits=0,
                requiresPremium=True,
                alreadySatisfied=True,
            )
        )

    if high_risk_requirements and request.preparation is None and "preparation_plan" not in artifacts:
        recommendations.append(
            AgentToolRecommendation(
                tool="preparation_plan",
                priority="critical",
                reason=f"{len(high_risk_requirements)} high-importance requirement(s) are weak or missing, so preparation should be generated next.",
                endpoint="/ai/preparation/plan",
                estimatedUnits=2,
                requiresPremium=True,
            )
        )
    elif request.preparation is not None or "preparation_plan" in artifacts:
        recommendations.append(
            AgentToolRecommendation(
                tool="preparation_plan",
                priority="low",
                reason="Preparation intelligence is already generated for this analysis.",
                endpoint="/ai/preparation/plan",
                estimatedUnits=0,
                requiresPremium=True,
                alreadySatisfied=True,
            )
        )

    if missing_requirements and "resume_rewrite" not in artifacts:
        recommendations.append(
            AgentToolRecommendation(
                tool="resume_rewrite",
                priority="high",
                reason=f"{len(missing_requirements)} requirement gap(s) need evidence-safe resume wording or explicit preparation handling.",
                endpoint="/ai/resume/rewrite",
                estimatedUnits=2,
                requiresPremium=True,
            )
        )
    elif "resume_rewrite" in artifacts:
        recommendations.append(
            AgentToolRecommendation(
                tool="resume_rewrite",
                priority="low",
                reason="Resume rewrite suggestions are already generated for this score.",
                endpoint="/ai/resume/rewrite",
                estimatedUnits=0,
                requiresPremium=True,
                alreadySatisfied=True,
            )
        )

    if "interview_questions" not in artifacts:
        recommendations.append(
            AgentToolRecommendation(
                tool="interview_questions",
                priority="medium",
                reason="Interview questions should be generated only after the score highlights the strongest and weakest topics.",
                endpoint="/ai/interview/questions",
                estimatedUnits=2,
                requiresPremium=True,
            )
        )

    if "cross_questions" not in artifacts:
        recommendations.append(
            AgentToolRecommendation(
                tool="cross_questions",
                priority="medium" if high_risk_requirements else "low",
                reason="Cross-questions help rehearse follow-ups for weak evidence and system design depth.",
                endpoint="/ai/cross-questions",
                estimatedUnits=2,
                requiresPremium=True,
            )
        )

    if "application_decision" not in artifacts:
        recommendations.append(
            AgentToolRecommendation(
                tool="application_decision",
                priority="medium" if request.researchNotes else "low",
                reason="Apply decisioning is most useful after score and research are present.",
                endpoint="/ai/application-decision",
                estimatedUnits=1,
                requiresPremium=True,
            )
        )

    if request.preparation is not None:
        recommendations.append(
            AgentToolRecommendation(
                tool="save_progress",
                priority="medium",
                reason="A preparation plan exists, so the next user action should be tracking daily progress.",
                endpoint="/history/preparation-sessions",
                estimatedUnits=0,
                requiresPremium=False,
            )
        )

    recommendations.sort(key=_recommendation_rank)
    top = next((item for item in recommendations if not item.alreadySatisfied), None)
    next_action = _format_next_action(top)
    headline = _headline(analysis.technicalMatchScore, high_risk_requirements, request.researchNotes)

    return CareerAgentPlanResponse(
        headline=headline,
        nextBestAction=next_action,
        reasoning=_reasoning(analysis.technicalMatchScore, weak_requirements, request.researchNotes, request.preparation),
        recommendations=recommendations,
        memorySignals=_memory_signals(request),
        guardrails=[
            "Run score first; optional tools should reuse the saved analysis instead of recomputing the full report.",
            "Do not generate resume claims from missing evidence; mark unsupported gaps as preparation work.",
            "Use cited or manually reviewed research before company-specific interview preparation.",
        ],
    )


def _weak_requirements(matches: list[RequirementMatch]) -> list[RequirementMatch]:
    return [match for match in matches if match.score < 60]


def _recommendation_rank(item: AgentToolRecommendation) -> tuple[int, int]:
    priority_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    return (1 if item.alreadySatisfied else 0, priority_rank[item.priority])


def _format_next_action(item: AgentToolRecommendation | None) -> str:
    if item is None:
        return "All core optional artifacts are already available. Track preparation progress and keep adding research notes."
    labels = {
        "research_note": "Generate or save a research note",
        "preparation_plan": "Build preparation intelligence",
        "resume_rewrite": "Build evidence-safe resume rewrite suggestions",
        "application_decision": "Build the apply/prep/skip decision",
        "interview_questions": "Generate interview questions",
        "cross_questions": "Generate cross-question chains",
        "gap_report": "Review the gap report",
        "score": "Run the free score",
        "save_progress": "Save preparation progress",
    }
    return labels[item.tool]


def _headline(score: int, high_risk_requirements: list[RequirementMatch], research_notes: list[object]) -> str:
    if high_risk_requirements:
        return "Close high-priority gaps before spending on deeper artifacts."
    if score >= 75 and research_notes:
        return "Strong enough to move into decisioning and interview preparation."
    if score >= 60:
        return "Good baseline score; add research before deeper preparation."
    return "Score shows partial fit; prioritize gaps before apply decisioning."


def _reasoning(
    score: int,
    weak_requirements: list[RequirementMatch],
    research_notes: list[object],
    preparation: object | None,
) -> list[str]:
    reasoning = [f"Current technical score is {score}%."]
    if weak_requirements:
        high_count = len([match for match in weak_requirements if match.importance == "high"])
        reasoning.append(f"{len(weak_requirements)} requirement(s) are below 60%, including {high_count} high-importance item(s).")
    else:
        reasoning.append("No requirement is currently below the 60% weak-evidence threshold.")
    reasoning.append(f"{len(research_notes)} research note(s) are available for context.")
    reasoning.append("Preparation intelligence is already available." if preparation else "Preparation intelligence has not been generated yet.")
    return reasoning


def _memory_signals(request: CareerAgentPlanRequest) -> list[str]:
    signals = [
        f"{len(request.researchNotes)} saved research note(s)",
        f"{len(request.generatedArtifacts)} generated optional artifact marker(s)",
    ]
    if request.company:
        signals.append(f"Company context: {request.company}")
    if request.roleTitle:
        signals.append(f"Role context: {request.roleTitle}")
    if request.preparation:
        signals.append(f"{len(request.preparation.dailyPlan)} preparation day(s) in memory")
    return signals
