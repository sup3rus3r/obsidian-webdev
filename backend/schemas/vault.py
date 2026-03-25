"""Secrets vault schemas."""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, field_validator


class ProviderType(str, Enum):
    anthropic = "anthropic"
    openai = "openai"
    ollama = "ollama"
    lmstudio = "lmstudio"
    obsidian_ai = "obsidian-ai"
    github_pat = "github_pat"
    gitlab_pat = "gitlab_pat"
    bitbucket_pat = "bitbucket_pat"


class SecretType(str, Enum):
    """Extended secret types including git credentials."""
    # AI providers (user-scoped)
    anthropic = "anthropic"
    openai = "openai"
    ollama = "ollama"
    lmstudio = "lmstudio"
    obsidian_ai = "obsidian-ai"
    # Git credentials (project-scoped)
    ssh_key = "ssh_key"
    git_pat = "git_pat"


class VaultKeyCreate(BaseModel):
    """Create or replace a stored secret.

    For cloud providers (anthropic, openai) `value` is the API key.
    For local providers (ollama, lmstudio) `value` is the base URL.
    For git_pat `value` is the personal access token.
    SSH keys are generated server-side via POST /vault/ssh/generate.
    """
    provider: ProviderType
    label: str
    value: str

    @field_validator("value")
    @classmethod
    def value_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("value must not be empty")
        return v.strip()


class VaultKeyResponse(BaseModel):
    """Public representation of a stored secret — value is NEVER included."""
    id: str
    provider: str
    label: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class VaultKeyListResponse(BaseModel):
    secrets: list[VaultKeyResponse]


class VaultValidateRequest(BaseModel):
    provider: ProviderType


class VaultValidateResponse(BaseModel):
    provider: str
    valid: bool
    message: str


# --- SSH / Git schemas ---

class SSHKeyGenerateRequest(BaseModel):
    project_id: str
    label: Optional[str] = None


class SSHKeyResponse(BaseModel):
    """Returned after generating or fetching an SSH keypair.
    Only the public key is exposed — private key stays encrypted in vault.
    """
    project_id: str
    public_key: str
    label: str
    created_at: datetime
    already_existed: bool = False


class GitPatCreate(BaseModel):
    """Store a personal access token scoped to a project."""
    project_id: str
    label: str
    token: str

    @field_validator("token")
    @classmethod
    def token_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("token must not be empty")
        return v.strip()
