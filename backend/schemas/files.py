"""Project file schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


class ProjectFileResponse(BaseModel):
    id: str
    project_id: str
    path: str
    content: str
    language: str = "text"
    summary: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class FileWriteRequest(BaseModel):
    path: str
    content: str

    @field_validator("path")
    @classmethod
    def path_safe(cls, v: str) -> str:
        v = v.strip().lstrip("/")
        if not v:
            raise ValueError("path must not be empty")
        if ".." in v.split("/"):
            raise ValueError("path must not contain '..'")
        return v


class FileListItem(BaseModel):
    """Lightweight file entry — content excluded for list performance."""
    id: str
    project_id: str
    path: str
    language: str = "text"
    summary: Optional[str] = None
    updated_at: Optional[datetime] = None


class FileListResponse(BaseModel):
    files: list[FileListItem]


class FileTreeNode(BaseModel):
    """Recursive tree node for rendering a directory tree."""
    name: str
    path: str
    type: str
    language: Optional[str] = None
    children: list[FileTreeNode] = []
