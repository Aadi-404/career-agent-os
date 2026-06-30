from pydantic import BaseModel

from app.models.history import UserRecord


class UserSessionResponse(BaseModel):
    user: UserRecord
    sessionToken: str
