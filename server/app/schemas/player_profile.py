from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.schemas.game import OrmModel


class PlayerProfileRead(OrmModel):
    id: int
    display_name: str
    slug: str
    pin_enabled: bool
    last_unlocked_at: Optional[datetime] = None
    failed_unlock_attempts: int
    locked_until: Optional[datetime] = None
    last_failed_unlock_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PlayerProfileCreate(BaseModel):
    display_name: str = Field(..., min_length=2, max_length=120)
    pin: Optional[str] = Field(None, min_length=4, max_length=12)


class ProfileUnlockPayload(BaseModel):
    pin: str = Field(..., min_length=4, max_length=12)


class ProfileUnlockResponse(BaseModel):
    token: str
    expires_at: datetime


class ProfilePinPayload(BaseModel):
    pin: str = Field(..., min_length=4, max_length=12)
    current_pin: Optional[str] = Field(None, min_length=4, max_length=12)


class ProfilePinDisablePayload(BaseModel):
    current_pin: Optional[str] = Field(None, min_length=4, max_length=12)
