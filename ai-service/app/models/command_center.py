from pydantic import BaseModel, Field

from app.models.history import WorkspaceSummary
from app.models.opportunity_intelligence import OpportunityNextActionsResponse
from app.models.prep_memory import PrepMemoryResponse
from app.models.system import ProductionReadinessResponse


class CommandCenterResponse(BaseModel):
    summary: str
    workspace: WorkspaceSummary
    preparationMemory: PrepMemoryResponse
    opportunityActions: OpportunityNextActionsResponse
    productionReadiness: ProductionReadinessResponse | None = None
    topActions: list[str] = Field(default_factory=list)
