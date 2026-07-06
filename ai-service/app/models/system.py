from typing import Literal

from pydantic import BaseModel, Field


class SystemDiagnostics(BaseModel):
    status: str
    environment: str
    databaseOk: bool
    llmMode: str
    llmProvider: str
    llmModel: str
    llmKeyConfigured: bool
    embeddingProvider: str
    embeddingModel: str
    embeddingFallbackLocal: bool
    jdParserMode: str
    corsOrigins: list[str] = Field(default_factory=list)
    workspaceCounts: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class ReadinessCheck(BaseModel):
    key: str
    label: str
    status: Literal["pass", "warn", "fail"]
    detail: str


class ProductionReadinessResponse(BaseModel):
    environment: str
    readyForProduction: bool
    checks: list[ReadinessCheck] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ExtensionPackageStatus(BaseModel):
    packaged: bool
    version: str | None = None
    apiBaseUrl: str | None = None
    webAppUrl: str | None = None
    packagedFor: str | None = None
    packagedAt: str | None = None
    unpackedPath: str | None = None
    zipPath: str | None = None
    message: str


class ReleaseSummaryResponse(BaseModel):
    environment: str
    readyForProduction: bool
    readinessBlockers: int
    readinessWarnings: int
    demoUserPresent: bool
    extensionPackage: ExtensionPackageStatus
    launchDecision: str
    nextActions: list[str] = Field(default_factory=list)
