from pydantic import BaseModel, Field, model_validator


ROLE_FAMILIES = [".NET", "Java", "Python", "Frontend", "Data/AI", "Cloud/DevOps", "General Software"]


class ScoringCalibrationConfig(BaseModel):
    userId: str
    roleFamily: str
    categoryWeights: dict[str, int] = Field(default_factory=dict)
    isDefault: bool = False
    updatedAt: str | None = None

    @model_validator(mode="after")
    def validate_weights(self):
        for category, weight in self.categoryWeights.items():
            if not category or weight < 0 or weight > 100:
                raise ValueError("Category weights must be named values between 0 and 100")
        return self


class ScoringCalibrationUpdateRequest(BaseModel):
    userId: str = Field(min_length=2, max_length=80)
    roleFamily: str = Field(min_length=2, max_length=80)
    categoryWeights: dict[str, int] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_weight_total(self):
        total = sum(self.categoryWeights.values())
        if total != 100:
            raise ValueError("Category weights must total 100")
        return self


class ScoringCalibrationListResponse(BaseModel):
    userId: str
    configs: list[ScoringCalibrationConfig] = Field(default_factory=list)


class ScoringCalibrationRecommendation(BaseModel):
    userId: str
    roleFamily: str
    currentWeights: dict[str, int] = Field(default_factory=dict)
    suggestedWeights: dict[str, int] = Field(default_factory=dict)
    confidence: str
    sampleSize: int
    reason: str
    changes: list[str] = Field(default_factory=list)
