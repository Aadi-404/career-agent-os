from app.models.history import JobOpportunityRecord
from app.models.opportunity_intelligence import OpportunityNextAction, OpportunityNextActionsResponse


def build_opportunity_next_actions(opportunities: list[JobOpportunityRecord]) -> OpportunityNextActionsResponse:
    actions = [_action_for_opportunity(opportunity) for opportunity in opportunities]
    filtered = [action for action in actions if action is not None]
    filtered.sort(key=_action_rank)
    return OpportunityNextActionsResponse(
        summary=_summary(filtered, opportunities),
        actions=filtered[:12],
    )


def _action_for_opportunity(opportunity: JobOpportunityRecord) -> OpportunityNextAction | None:
    status = opportunity.status
    score = opportunity.technicalMatchScore
    artifacts = opportunity.optionalArtifacts or {}

    if status in {"rejected", "archived"}:
        return None
    if status == "offer":
        return _action(
            opportunity,
            priority="medium",
            action="Prepare offer negotiation notes",
            reason="Offer-stage opportunities should move into compensation, joining-date, and counter-offer planning.",
        )
    if score is None:
        return _action(
            opportunity,
            priority="high",
            action="Run score before pipeline decision",
            reason="This opportunity has no saved match score, so apply/skip decisions are weak.",
        )
    if status == "viewed" and score < 45:
        return _action(
            opportunity,
            recommended_status="archived",
            priority="medium",
            action="Archive or skip low-fit job",
            reason=f"Technical match is {score}%, below the selective-apply threshold.",
        )
    if status == "viewed" and score >= 70:
        return _action(
            opportunity,
            recommended_status="shortlisted",
            priority="high",
            action="Shortlist this role",
            reason=f"Technical match is {score}%, strong enough to prioritize.",
        )
    if status == "viewed":
        return _missing_artifact_action(opportunity, "resume_improvements", "Build resume improvements before deciding", "Score is moderate, so improve evidence before applying.")

    if status == "shortlisted":
        if "resume_improvements" not in artifacts:
            return _missing_artifact_action(opportunity, "resume_improvements", "Build resume improvements", "Shortlisted roles need tailored evidence before apply.")
        if "interview_questions" not in artifacts:
            return _missing_artifact_action(opportunity, "interview_questions", "Build interview questions", "Prepare likely interview topics before applying.")
        return _action(
            opportunity,
            recommended_status="applied",
            priority="medium",
            action="Apply and update status",
            reason="Core shortlist artifacts are ready.",
        )

    if status == "applied":
        if "interview_questions" not in artifacts:
            return _missing_artifact_action(opportunity, "interview_questions", "Build interview questions", "Applied roles should have interview prep ready before recruiter callbacks.")
        return _action(
            opportunity,
            recommended_status="interview",
            priority="low",
            action="Move to interview when callback is received",
            reason="Application is already sent; keep tracking recruiter response.",
        )

    if status == "interview":
        if "cross_questions" not in artifacts:
            return _missing_artifact_action(opportunity, "cross_questions", "Build cross-question chains", "Interview-stage roles need follow-up practice and depth checks.")
        return _action(
            opportunity,
            priority="high",
            action="Track interview follow-up",
            reason="Interview prep artifacts exist; focus on feedback, next round, and follow-up notes.",
        )

    return None


def _missing_artifact_action(
    opportunity: JobOpportunityRecord,
    artifact_key: str,
    action: str,
    reason: str,
) -> OpportunityNextAction:
    endpoints = {
        "resume_improvements": "/ai/resume-improvements",
        "interview_questions": "/ai/interview/questions",
        "cross_questions": "/ai/cross-questions",
    }
    return _action(
        opportunity,
        artifact_key=artifact_key,
        endpoint=endpoints[artifact_key],
        priority="high" if opportunity.status in {"shortlisted", "interview"} else "medium",
        action=action,
        reason=reason,
    )


def _action(
    opportunity: JobOpportunityRecord,
    *,
    priority: str,
    action: str,
    reason: str,
    recommended_status: str | None = None,
    artifact_key: str | None = None,
    endpoint: str | None = None,
) -> OpportunityNextAction:
    return OpportunityNextAction(
        opportunityId=opportunity.id,
        title=opportunity.title,
        company=opportunity.company,
        currentStatus=opportunity.status,
        recommendedStatus=recommended_status,
        artifactKey=artifact_key,
        endpoint=endpoint,
        priority=priority,
        action=action,
        reason=reason,
        score=opportunity.technicalMatchScore,
    )


def _action_rank(action: OpportunityNextAction) -> tuple[int, int]:
    priority_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    status_rank = {"interview": 0, "shortlisted": 1, "applied": 2, "viewed": 3, "offer": 4}
    return (priority_rank[action.priority], status_rank.get(action.currentStatus, 9))


def _summary(actions: list[OpportunityNextAction], opportunities: list[JobOpportunityRecord]) -> str:
    active_count = len([item for item in opportunities if item.status not in {"rejected", "archived"}])
    if not opportunities:
        return "No job opportunities are saved yet. Match jobs from the extension to build the pipeline."
    if not actions:
        return f"{active_count} active opportunity record(s), with no immediate action detected."
    high_count = len([item for item in actions if item.priority in {"critical", "high"}])
    return f"{len(actions)} recommended next action(s) across {active_count} active opportunity record(s), including {high_count} high-priority item(s)."
