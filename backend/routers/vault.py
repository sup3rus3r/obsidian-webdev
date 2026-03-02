"""Secrets vault router."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core.rate_limiter import limiter, user_limit
from core.security import TokenData, get_current_user
from database.sql import get_db
from schemas.vault import (
    VaultKeyCreate,
    VaultKeyListResponse,
    VaultKeyResponse,
    VaultValidateRequest,
    VaultValidateResponse,
)
from services.vault_service import VaultService

router = APIRouter(prefix="/vault", tags=["vault"])


@router.get("/secrets", response_model=VaultKeyListResponse)
@limiter.limit(user_limit())
async def list_secrets(
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all stored API keys for the current user (labels only, no values)."""
    return await VaultService.list_secrets(current_user.user_id, db)


@router.post("/secrets", response_model=VaultKeyResponse)
@limiter.limit(user_limit())
async def upsert_secret(
    payload: VaultKeyCreate,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Store or replace an API key for a provider. Encrypted at rest via Fernet."""
    return await VaultService.upsert_secret(current_user.user_id, payload, db)


@router.delete("/secrets/{provider}")
@limiter.limit(user_limit())
async def delete_secret(
    provider: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Soft-delete a stored secret."""
    return await VaultService.delete_secret(current_user.user_id, provider, db)


@router.post("/secrets/validate", response_model=VaultValidateResponse)
@limiter.limit("10/minute")
async def validate_secret(
    payload: VaultValidateRequest,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Test a stored API key against the provider's live API."""
    return await VaultService.validate_secret(current_user.user_id, payload.provider, db)
