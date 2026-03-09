"""Project schemas."""
from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, field_validator


class Framework(str, Enum):
    blank = "blank"
    react = "react"
    nextjs = "nextjs"
    fastapi = "fastapi"
    fullstack = "fullstack"


class ProjectStatus(str, Enum):
    idle = "idle"
    building = "building"
    preparing = "preparing"
    running = "running"
    stopped = "stopped"
    error = "error"


class BuildStatus(str, Enum):
    none = "none"
    running = "running"
    passed = "passed"
    failed = "failed"


class ModelProvider(str, Enum):
    anthropic = "anthropic"
    openai = "openai"
    ollama = "ollama"
    lmstudio = "lmstudio"


PROVIDER_MODELS: dict[str, list[str]] = {
    "anthropic": [
        "claude-opus-4-6",
        "claude-sonnet-4-6",
        "claude-haiku-4-5-20251001",
    ],
    "openai": [
        "gpt-5.2",
        "gpt-5.2-pro",
        "gpt-5",
        "gpt-5-pro",
        "gpt-5-mini",
        "gpt-5-nano",
        "gpt-4.1",
        "gpt-4.1-mini",
        "gpt-4.1-nano",
        "o3",
        "o3-mini",
        "o3-pro",
        "o4-mini",
    ],
    "ollama": [],
    "lmstudio": [],
}


class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    framework: Framework = Framework.blank
    model_provider: ModelProvider = ModelProvider.anthropic
    model_id: str = "claude-sonnet-4-6"

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Project name must not be empty")
        if len(v) > 100:
            raise ValueError("Project name must be 100 characters or fewer")
        return v

    @field_validator("model_id")
    @classmethod
    def model_id_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("model_id must not be empty")
        return v


class ProjectImportGitHub(BaseModel):
    name: str
    description: str = ""
    model_provider: ModelProvider = ModelProvider.anthropic
    model_id: str = "claude-sonnet-4-6"
    github_url: str

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Project name must not be empty")
        if len(v) > 100:
            raise ValueError("Project name must be 100 characters or fewer")
        return v

    @field_validator("model_id")
    @classmethod
    def model_id_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("model_id must not be empty")
        return v

    @field_validator("github_url")
    @classmethod
    def github_url_valid(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("github_url must not be empty")
        if not (v.startswith("https://") or v.startswith("http://")):
            raise ValueError("github_url must be a valid HTTP/HTTPS URL")
        return v


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    model_provider: Optional[ModelProvider] = None
    model_id: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Project name must not be empty")
            if len(v) > 100:
                raise ValueError("Project name must be 100 characters or fewer")
        return v


class ProjectResponse(BaseModel):
    id: str
    owner_id: str
    name: str
    description: str
    framework: str
    model_provider: str
    model_id: str
    status: str
    build_status: str
    container_id: Optional[str] = None
    host_port: Optional[int] = None
    host_ports: Optional[dict] = None
    template_ready: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None


class ProjectListResponse(BaseModel):
    projects: list[ProjectResponse]


class AgentSessionResponse(BaseModel):
    id: str
    project_id: str
    user_id: str
    thread_id: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
