"""Auth & user-management schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class EncryptedRequest(BaseModel):
    """Request body carrying AES-encrypted payload from the frontend."""
    encrypted: str


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str = "admin"


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class APIClientCreate(BaseModel):
    name: str


class APIClientResponse(BaseModel):
    id: str
    name: str
    client_id: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class APIClientCreateResponse(BaseModel):
    """Shown only once at creation — includes the plain-text client_secret."""
    id: str
    name: str
    client_id: str
    client_secret: str
    is_active: bool
    created_at: datetime
    message: str = "Store the client_secret securely. It will not be shown again."


class APIClientListResponse(BaseModel):
    clients: list[APIClientResponse]


class UserDetailsResponse(BaseModel):
    id: str
    username: str
    email: str
    role: Optional[str] = None
    auth_type: str
    client_name: Optional[str] = None


class ToggleRoleResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
    message: str


class UpdateProfileRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None


class UpdateProfileResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str

    model_config = {"from_attributes": True}


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
