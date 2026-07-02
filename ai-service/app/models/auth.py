from typing import Literal

from pydantic import BaseModel, Field

from app.models.history import UserRecord


class UserSessionResponse(BaseModel):
    user: UserRecord
    sessionToken: str


class UserPasswordRegisterRequest(BaseModel):
    userId: str = Field(min_length=2, max_length=80)
    displayName: str = Field(min_length=2, max_length=120)
    email: str | None = Field(default=None, max_length=180)
    password: str = Field(min_length=8, max_length=160)
    role: Literal["member", "admin"] | None = None
    subscriptionTier: Literal["free", "premium"] | None = None


class UserLoginRequest(BaseModel):
    userIdOrEmail: str = Field(min_length=2, max_length=180)
    password: str = Field(min_length=8, max_length=160)
