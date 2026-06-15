from pydantic import BaseModel


class ResumeExtractResponse(BaseModel):
    fileName: str
    contentType: str | None
    extractedText: str
    characterCount: int
    detectedEmails: list[str]
    detectedPhones: list[str]
    detectedSections: list[str]
