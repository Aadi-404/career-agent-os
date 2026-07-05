from app.models.command_center import CommandCenterResponse
from app.models.history import AnalysisRecord, JobOpportunityRecord, PreparationSessionRecord, WorkspaceSummary
from app.models.opportunity_intelligence import OpportunityNextActionsResponse
from app.models.prep_memory import PrepMemoryResponse
from app.services.opportunity_intelligence_service import build_opportunity_next_actions
from app.services.prep_memory_service import build_prep_memory


def build_command_center(
    workspace: WorkspaceSummary,
    analyses: list[AnalysisRecord],
    preparation_sessions: list[PreparationSessionRecord],
    opportunities: list[JobOpportunityRecord],
) -> CommandCenterResponse:
    prep_memory = build_prep_memory(analyses, preparation_sessions)
    opportunity_actions = build_opportunity_next_actions(opportunities)
    top_actions = _top_actions(workspace, prep_memory, opportunity_actions)
    return CommandCenterResponse(
        summary=_summary(workspace, prep_memory, opportunity_actions),
        workspace=workspace,
        preparationMemory=prep_memory,
        opportunityActions=opportunity_actions,
        topActions=top_actions,
    )


def _top_actions(
    workspace: WorkspaceSummary,
    prep_memory: PrepMemoryResponse,
    opportunity_actions: OpportunityNextActionsResponse,
) -> list[str]:
    actions = []
    if workspace.latestAnalysis is None:
        actions.append("Run a score-only resume/JD match.")
    if prep_memory.nextAction:
        actions.append(prep_memory.nextAction.label)
    if opportunity_actions.actions:
        actions.append(opportunity_actions.actions[0].action)
    if not actions:
        actions.append("Refresh history after saving new scores, prep progress, or extension matches.")
    return actions[:5]


def _summary(
    workspace: WorkspaceSummary,
    prep_memory: PrepMemoryResponse,
    opportunity_actions: OpportunityNextActionsResponse,
) -> str:
    if workspace.latestAnalysis is None:
        return "No saved score exists yet. Start with score-only resume matching."
    if prep_memory.nextAction and opportunity_actions.actions:
        return "Command Center has preparation and pipeline actions ready."
    if prep_memory.nextAction:
        return "Command Center has a preparation action ready."
    if opportunity_actions.actions:
        return "Command Center has application pipeline actions ready."
    return "Workspace is up to date; save more analyses or job matches to generate new actions."
