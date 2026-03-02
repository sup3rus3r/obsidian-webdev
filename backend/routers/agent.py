"""Agent session management router.

HTTP API for creating and querying agent sessions.
The WebSocket endpoint (/ws/agent/{session_id}) handles real-time streaming
and is the primary way to start and stop the agent.

Endpoints:
  POST   /agent/sessions                  — create a session
  GET    /agent/sessions/{session_id}     — get session info
  GET    /agent/sessions?project_id=...   — list sessions for a project
  POST   /agent/sessions/{session_id}/stop — cancel the running task
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from core.rate_limiter import limiter, user_limit
from core.security import TokenData, get_current_user
from database.mongo import get_database
from models.mongo_models import AgentSessionCollection, ProjectCollection
from schemas.agent import (
    AgentSessionCreate,
    AgentSessionResponse,
)
import services.agent_runner as runner

router = APIRouter(prefix="/agent/sessions", tags=["agent"])


def _session_to_response(doc: dict) -> AgentSessionResponse:
    return AgentSessionResponse(
        session_id=str(doc["_id"]),
        project_id=doc["project_id"],
        user_id=doc["user_id"],
        status=doc.get("status", "idle"),
        model_provider=doc.get("model_provider", "openai"),
        model_id=doc.get("model_id", "gpt-4.1"),
        created_at=doc.get("created_at"),
    )


async def _get_session_or_404(db, session_id: str, user_id: str) -> dict:
    try:
        doc = await AgentSessionCollection.find_by_id(db, session_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Session not found")
    if not doc or doc.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Session not found")
    return doc


@router.post("", response_model=AgentSessionResponse, status_code=201)
@limiter.limit(user_limit())
async def create_session(
    payload: AgentSessionCreate,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Create a new agent session for a project."""
    db = get_database()
    try:
        project = await ProjectCollection.find_by_id(db, payload.project_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project or project.get("owner_id") != current_user.user_id:
        raise HTTPException(status_code=404, detail="Project not found")

    doc = await AgentSessionCollection.create(db, {
        "project_id": payload.project_id,
        "user_id": current_user.user_id,
        "status": "idle",
        "model_provider": payload.model_provider,
        "model_id": payload.model_id,
        "created_at": datetime.now(timezone.utc),
    })
    return _session_to_response(doc)


@router.get("/{session_id}", response_model=AgentSessionResponse)
@limiter.limit(user_limit())
async def get_session(
    session_id: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    db = get_database()
    doc = await _get_session_or_404(db, session_id, current_user.user_id)
    return _session_to_response(doc)


@router.get("", response_model=list[AgentSessionResponse])
@limiter.limit(user_limit())
async def list_sessions(
    project_id: str = Query(..., description="Filter by project ID"),
    request: Request = None,
    current_user: TokenData = Depends(get_current_user),
):
    db = get_database()
    docs = await AgentSessionCollection.find_by_project(db, project_id)
    return [
        _session_to_response(d)
        for d in docs
        if d.get("user_id") == current_user.user_id
    ]


@router.post("/{session_id}/stop", status_code=204)
@limiter.limit(user_limit())
async def stop_session(
    session_id: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Cancel the running agent task for a session."""
    db = get_database()
    await _get_session_or_404(db, session_id, current_user.user_id)
    await runner.stop_agent(session_id)
