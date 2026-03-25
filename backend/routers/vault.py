"""Secrets vault router."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core.rate_limiter import limiter, user_limit
from core.security import TokenData, get_current_user
from database.sql import get_db
from schemas.vault import (
    GitPatCreate,
    SSHKeyGenerateRequest,
    SSHKeyResponse,
    VaultKeyCreate,
    VaultKeyListResponse,
    VaultKeyResponse,
    VaultValidateRequest,
    VaultValidateResponse,
)
from services.vault_service import ProjectSecretService, VaultService

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


# --- SSH key endpoints ---

@router.post("/ssh/generate", response_model=SSHKeyResponse)
@limiter.limit(user_limit())
async def generate_ssh_key(
    payload: SSHKeyGenerateRequest,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate an ED25519 SSH keypair for a project.
    Private key is encrypted and stored; public key is returned for the user to add to GitHub/GitLab.
    If a key already exists for this project it is returned unchanged (already_existed=true).
    """
    return await ProjectSecretService.generate_ssh_keypair(current_user.user_id, payload, db)


@router.get("/ssh/public-key/{project_id}", response_model=SSHKeyResponse)
@limiter.limit(user_limit())
async def get_ssh_public_key(
    project_id: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the SSH public key for a project (safe to display/copy)."""
    return await ProjectSecretService.get_ssh_public_key(current_user.user_id, project_id, db)


@router.delete("/ssh/{project_id}")
@limiter.limit(user_limit())
async def delete_ssh_key(
    project_id: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Soft-delete the SSH keypair for a project."""
    return await ProjectSecretService.delete_project_secret(current_user.user_id, project_id, "ssh_key", db)


# --- PAT endpoints ---

@router.post("/pat", response_model=SSHKeyResponse)
@limiter.limit(user_limit())
async def store_git_pat(
    payload: GitPatCreate,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Store a personal access token for a project (for HTTPS git auth)."""
    return await ProjectSecretService.store_git_pat(current_user.user_id, payload, db)


@router.delete("/pat/{project_id}")
@limiter.limit(user_limit())
async def delete_git_pat(
    project_id: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove the stored PAT for a project."""
    return await ProjectSecretService.delete_project_secret(current_user.user_id, project_id, "git_pat", db)
