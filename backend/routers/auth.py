"""Auth & user-management router."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from config import settings
from core.security import (
    TokenData,
    APIClientData,
    get_current_user,
    get_current_user_or_api_client,
)
from core.rate_limiter import limiter, user_limit, api_client_limit
from database.sql import get_db
from schemas.auth import (
    EncryptedRequest,
    APIClientCreate,
    APIClientCreateResponse,
    APIClientListResponse,
    LoginResponse,
    RefreshResponse,
    UserDetailsResponse,
    UserResponse,
    ToggleRoleResponse,
    UpdateProfileRequest,
    UpdateProfileResponse,
    ChangePasswordRequest,
)
from services.auth_service import AuthService

router = APIRouter(tags=["auth"])


@router.post("/auth/register", response_model=UserResponse)
async def register(request: EncryptedRequest, db: Session = Depends(get_db)):
    """Register a new user account."""
    return await AuthService.register_user(request.encrypted, db)


@router.post("/auth/login", response_model=LoginResponse)
async def login(request: EncryptedRequest, db: Session = Depends(get_db)):
    """Login and receive a JWT access token."""
    return await AuthService.login_user(request.encrypted, db)


@router.post("/auth/refresh", response_model=RefreshResponse)
@limiter.limit("30/minute")
async def refresh_token(
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Exchange a valid JWT for a fresh one with a new expiry."""
    from datetime import timedelta
    from core.security import create_access_token
    new_token = create_access_token(
        data={
            "user_id": current_user.user_id,
            "username": current_user.username,
            "role": current_user.role,
            "token_type": "user",
        },
        expires_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return RefreshResponse(
        access_token=new_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/health")
@limiter.limit(user_limit())
async def health_check(
    request: Request,
    auth: TokenData | APIClientData = Depends(get_current_user_or_api_client),
):
    """Health check — accepts JWT or API key/secret."""
    return {
        "status": "ok",
        "authenticated_as": auth.username if isinstance(auth, TokenData) else auth.client_name,
        "auth_type": auth.token_type,
    }


@router.get("/get_user_details", response_model=UserDetailsResponse)
@limiter.limit(user_limit())
async def get_user_details(
    request: Request,
    auth: TokenData | APIClientData = Depends(get_current_user_or_api_client),
    db: Session = Depends(get_db),
):
    """Get details for the authenticated user or API client."""
    if isinstance(auth, TokenData):
        return await AuthService.get_user_details(auth.user_id, db)
    return UserDetailsResponse(
        id=auth.client_id,
        username=auth.client_name,
        email="",
        auth_type="api_client",
        client_name=auth.client_name,
    )


@router.put("/user/toggle-role", response_model=ToggleRoleResponse)
@limiter.limit("10/minute")
async def toggle_role(
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Toggle the current user's role between 'admin' and 'guest'."""
    return await AuthService.toggle_role(current_user.user_id, current_user.role, current_user.username, db)


@router.put("/user/profile", response_model=UpdateProfileResponse)
@limiter.limit(user_limit())
async def update_profile(
    request: Request,
    body: UpdateProfileRequest,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the current user's username and/or email."""
    return await AuthService.update_profile(current_user.user_id, body.username, body.email, db)


@router.put("/user/password")
@limiter.limit("10/minute")
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change the current user's password."""
    return await AuthService.change_password(current_user.user_id, body.current_password, body.new_password, db)


@router.post("/api-clients", response_model=APIClientCreateResponse)
async def create_api_client(
    client_data: APIClientCreate,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new API client. The secret is only returned once."""
    return await AuthService.create_api_client(client_data.name, current_user.user_id, db)


@router.get("/api-clients", response_model=APIClientListResponse)
async def list_api_clients(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all API clients belonging to the current user."""
    return await AuthService.list_api_clients(current_user.user_id, db)


@router.delete("/api-clients/{client_id}")
async def revoke_api_client(
    client_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revoke (deactivate) an API client."""
    return await AuthService.revoke_api_client(client_id, current_user.user_id, db)
