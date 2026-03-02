"""Workspace WebSocket router."""
from fastapi import APIRouter

router = APIRouter(prefix="/ws", tags=["workspace"])

