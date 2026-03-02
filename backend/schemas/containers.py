"""Container management schemas."""
from typing import Optional

from pydantic import BaseModel


class ContainerStartResponse(BaseModel):
    project_id: str
    container_id: str
    host_port: Optional[int] = None
    status: str
    files_restored: int


class ContainerStatusResponse(BaseModel):
    project_id: str
    container_id: Optional[str] = None
    host_port: Optional[int] = None
    status: str


class ExecRequest(BaseModel):
    cmd: str
    workdir: str = "/workspace"


class ExecResponse(BaseModel):
    exit_code: int
    output: str
