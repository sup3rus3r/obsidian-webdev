"""SQLAlchemy 2.0 ORM models (SQLite / PostgreSQL)."""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from database.sql import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(50), server_default="guest")
    hashed_password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class APIClient(Base):
    """API clients for external access with client_id / client_secret auth."""

    __tablename__ = "api_clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    client_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_secret: Mapped[str] = mapped_column(String(255))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


VAULT_KEY_VERSION = 1


class UserSecret(Base):
    """Fernet-encrypted user API keys. One active secret per (user_id, provider)."""

    __tablename__ = "user_secrets"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_user_secrets_user_provider"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    provider: Mapped[str] = mapped_column(String(50))
    label: Mapped[str] = mapped_column(String(255))
    encrypted_value: Mapped[str] = mapped_column(Text)
    key_version: Mapped[int] = mapped_column(Integer, default=VAULT_KEY_VERSION)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )


class ProjectSecret(Base):
    """Fernet-encrypted project-scoped secrets (SSH keys, PATs).

    Keyed on (user_id, project_id, secret_type) — one active secret per type per project.
    """

    __tablename__ = "project_secrets"
    __table_args__ = (
        UniqueConstraint("user_id", "project_id", "secret_type", name="uq_project_secrets_user_project_type"),
        Index("ix_project_secrets_project_id", "project_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    project_id: Mapped[str] = mapped_column(String(100))
    secret_type: Mapped[str] = mapped_column(String(50))  # "ssh_key", "git_pat"
    label: Mapped[str] = mapped_column(String(255))
    encrypted_value: Mapped[str] = mapped_column(Text)     # private key or PAT
    public_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # SSH public key (safe to expose)
    key_version: Mapped[int] = mapped_column(Integer, default=VAULT_KEY_VERSION)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )
