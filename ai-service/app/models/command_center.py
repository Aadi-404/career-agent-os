from pydantic import BaseModel, Field

from app.models.history import WorkspaceSummary
from app.models.opportunity_intelligence import OpportunityNextActionsResponse
from app.models.prep_memory import PrepMemoryResponse


class CommandCenterResponse(BaseModel):
    summary: str
    workspace: WorkspaceSummary
    preparationMemory: PrepMemoryResponse
    opportunityActions: OpportunityNextActionsResponse
    topActions: list[str] = Field(default_factory=list)
