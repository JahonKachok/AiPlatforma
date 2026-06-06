from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime
from app.models.user import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: UserRole = UserRole.designer
    department: Optional[str] = None
    phone: Optional[str] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    department: Optional[str] = None
    phone: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: str
    role: UserRole
    department: Optional[str]
    phone: Optional[str]
    avatar_url: Optional[str]
    telegram_chat_id: Optional[str]
    is_active: bool
    two_factor_enabled: bool
    created_at: datetime


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshRequest(BaseModel):
    refresh_token: str


class TwoFactorSetupResponse(BaseModel):
    secret: str
    qr_url: str
    qr_image_base64: str


class TwoFactorVerifyRequest(BaseModel):
    code: str


class LoginJournalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    status: str
    created_at: datetime


class UserStatsResponse(BaseModel):
    tasks_total: int
    tasks_completed: int
    tasks_in_progress: int
    tasks_overdue: int
    active_projects: int
