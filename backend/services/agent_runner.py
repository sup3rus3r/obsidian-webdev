"""Agent session management — plain asyncio, no LangGraph.

Each WebSocket session gets an AgentSession that tracks:
  - Conversation history (mutated by the agent loop)
  - A stop_event for clean cancellation
  - Pending HITL approval futures
  - The running asyncio.Task

Conversation history (both LLM messages and chat display) is persisted to
MongoDB keyed by project_id so it survives WebSocket reconnects.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


def _serialize_messages(messages: list) -> list:
    """Convert the LLM messages list to plain JSON-serializable dicts.

    Anthropic SDK content blocks (TextBlock, ToolUseBlock, …) are Pydantic
    models — call .model_dump() so they round-trip through MongoDB correctly.
    When loaded back as plain dicts the Anthropic API still accepts them.
    """
    out = []
    for msg in messages:
        m = dict(msg)
        content = m.get("content")
        if isinstance(content, list):
            m["content"] = [
                b.model_dump() if hasattr(b, "model_dump") else b
                for b in content
            ]
        out.append(m)
    return out


@dataclass
class AgentSession:
    project_id: str
    container_id: str
    model_provider: str
    model_id: str
    api_key: str
    permission_mode: str = "ask"
    messages: list[dict] = field(default_factory=list)
    display_messages: list[dict] = field(default_factory=list)
    stop_event: asyncio.Event = field(default_factory=asyncio.Event)
    pending_approvals: dict[str, asyncio.Future] = field(default_factory=dict)
    pending_clarifications: dict[str, asyncio.Future] = field(default_factory=dict)
    task: asyncio.Task | None = None
    agent: object | None = None


_sessions: dict[str, AgentSession] = {}


def _get_or_create(
    session_id: str,
    project_id: str,
    container_id: str,
    model_provider: str,
    model_id: str,
    api_key: str,
) -> AgentSession:
    if session_id not in _sessions:
        _sessions[session_id] = AgentSession(
            project_id=project_id,
            container_id=container_id,
            model_provider=model_provider,
            model_id=model_id,
            api_key=api_key,
        )
    else:
        s = _sessions[session_id]
        s.model_provider = model_provider
        s.model_id = model_id
        s.api_key = api_key
        s.container_id = container_id
    return _sessions[session_id]


def remove_session(session_id: str) -> None:
    _sessions.pop(session_id, None)


async def _load_conversation(session: AgentSession) -> None:
    """Load LLM messages + display history from MongoDB into the session."""
    try:
        from database.mongo import get_database
        from models.mongo_models import ProjectConversationCollection
        db = get_database()
        doc = await ProjectConversationCollection.find_by_project(db, session.project_id)
        if doc:
            session.messages = doc.get("messages", [])
            session.display_messages = doc.get("display", [])
    except Exception:
        logger.exception("Failed to load conversation for project %s", session.project_id)


async def _save_conversation(session: AgentSession) -> None:
    """Persist LLM messages + display history to MongoDB."""
    try:
        from database.mongo import get_database
        from models.mongo_models import ProjectConversationCollection
        db = get_database()
        await ProjectConversationCollection.upsert(
            db,
            session.project_id,
            _serialize_messages(session.messages),
            session.display_messages,
        )
    except Exception:
        logger.exception("Failed to save conversation for project %s", session.project_id)


async def get_display_history(project_id: str) -> list[dict]:
    """Return the stored display messages for a project (used by WS on connect)."""
    try:
        from database.mongo import get_database
        from models.mongo_models import ProjectConversationCollection
        db = get_database()
        doc = await ProjectConversationCollection.find_by_project(db, project_id)
        if doc:
            return doc.get("display", [])
    except Exception:
        logger.exception("Failed to fetch display history for project %s", project_id)
    return []


async def clear_conversation(project_id: str) -> None:
    """Wipe persisted conversation for a project (e.g. user requests fresh start)."""
    try:
        from database.mongo import get_database
        from models.mongo_models import ProjectConversationCollection
        db = get_database()
        await ProjectConversationCollection.clear(db, project_id)
    except Exception:
        logger.exception("Failed to clear conversation for project %s", project_id)

    for session in _sessions.values():
        if session.project_id == project_id:
            session.messages.clear()
            session.display_messages.clear()


async def start_agent(
    *,
    session_id: str,
    prompt: str,
    project_name: str,
    framework: str,
    send_event,
    project_id: str,
    container_id: str,
    model_provider: str,
    model_id: str,
    api_key: str,
    permission_mode: str = "ask",
    max_bash_lines: int = 400,
    max_file_lines: int = 500,
    max_web_chars: int = 20_000,
    compact_threshold: float = 0.80,
) -> None:
    """Cancel any running agent task and start a new one."""
    await stop_agent(session_id)

    is_new = session_id not in _sessions
    session = _get_or_create(
        session_id, project_id, container_id, model_provider, model_id, api_key
    )


    if is_new:
        session.permission_mode = permission_mode
    session.stop_event.clear()


    if not session.messages:
        await _load_conversation(session)

    from agents.agent import Agent

    async def _request_approval(approval_id: str, tool_name: str, params: dict) -> bool:
        loop = asyncio.get_event_loop()
        future: asyncio.Future = loop.create_future()
        session.pending_approvals[approval_id] = future
        try:
            return await asyncio.wait_for(asyncio.shield(future), timeout=1800)
        except asyncio.TimeoutError:
            return False
        finally:
            session.pending_approvals.pop(approval_id, None)

    async def _request_clarification(clarification_id: str, question: str) -> str:
        loop = asyncio.get_event_loop()
        future: asyncio.Future = loop.create_future()
        session.pending_clarifications[clarification_id] = future
        try:
            return await asyncio.wait_for(asyncio.shield(future), timeout=1800)
        except asyncio.TimeoutError:
            return "(clarification timed out — proceeding with best assumption)"
        finally:
            session.pending_clarifications.pop(clarification_id, None)


    token_buf: list[str] = [""]
    used_tools: list[bool] = [False]

    def _flush_token_buf() -> None:
        text = token_buf[0].strip()
        if text:
            session.display_messages.append({"role": "agent", "content": token_buf[0]})
        token_buf[0] = ""

    async def capturing_send(event: dict) -> None:
        etype = event.get("type")
        if etype == "token":
            token_buf[0] += event.get("content", "")
        elif etype == "tool_call":
            _flush_token_buf()
            used_tools[0] = True
            session.display_messages.append({
                "role": "tool",
                "content": "",
                "meta": {"tool": event.get("tool"), "params": event.get("params")},
            })
        elif etype == "tool_result":
            session.display_messages.append({
                "role": "tool_result",
                "content": event.get("result", ""),
                "meta": {"tool": event.get("tool"), "denied": event.get("denied", False)},
            })
        elif etype == "file_changed":
            session.display_messages.append({
                "role": "file",
                "content": event.get("path", ""),
            })
        elif etype == "compacting":
            _flush_token_buf()
            session.display_messages.append({"role": "compacting", "content": "Compacting conversation context…"})
        elif etype == "done":
            _flush_token_buf()
            if used_tools[0]:
                session.display_messages.append({"role": "done", "content": ""})
            used_tools[0] = False
        elif etype == "stopped":
            _flush_token_buf()
            session.display_messages.append({"role": "stopped", "content": "Agent stopped."})

        await send_event(event)


    session.display_messages.append({"role": "user", "content": prompt})

    agent = Agent(
        project_id=session.project_id,
        container_id=session.container_id,
        project_name=project_name,
        framework=framework,
        model_provider=session.model_provider,
        model_id=session.model_id,
        api_key=session.api_key,
        on_event=capturing_send,
        request_approval=_request_approval,
        request_clarification=_request_clarification,
        permission_mode=session.permission_mode,
        max_bash_lines=max_bash_lines,
        max_file_lines=max_file_lines,
        max_web_chars=max_web_chars,
        compact_threshold=compact_threshold,
    )

    async def _run() -> None:
        try:
            await agent.run(prompt, session.messages, session.stop_event)
        except asyncio.CancelledError:
            try:
                await send_event({"type": "stopped"})
            except Exception:
                pass
        except Exception as exc:
            logger.exception("Agent task raised exception for session %s", session_id)
            try:
                await send_event({"type": "error", "message": str(exc)})
            except Exception:
                pass
        finally:

            await _save_conversation(session)

    session.agent = agent
    session.task = asyncio.create_task(_run())


async def stop_agent(session_id: str) -> None:
    """Stop the running agent cleanly: deny pending approvals, cancel the task."""
    session = _sessions.get(session_id)
    if not session:
        return
    session.stop_event.set()
    for future in list(session.pending_approvals.values()):
        if not future.done():
            future.set_result(False)
    session.pending_approvals.clear()
    for future in list(session.pending_clarifications.values()):
        if not future.done():
            future.set_result("(agent stopped)")
    session.pending_clarifications.clear()
    if session.task and not session.task.done():
        session.task.cancel()
        try:
            await asyncio.wait_for(asyncio.shield(session.task), timeout=5.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass
    session.task = None
    session.agent = None


def resolve_approval(session_id: str, approval_id: str, approved: bool) -> None:
    """Called by the WS handler when the user approves or denies a tool call."""
    session = _sessions.get(session_id)
    if not session:
        return
    future = session.pending_approvals.get(approval_id)
    if future and not future.done():
        future.set_result(approved)


def resolve_clarification(session_id: str, clarification_id: str, answer: str) -> None:
    """Called by the WS handler when the user answers a clarification question."""
    session = _sessions.get(session_id)
    if not session:
        return
    future = session.pending_clarifications.get(clarification_id)
    if future and not future.done():
        future.set_result(answer)


def set_permission_mode(session_id: str, mode: str) -> None:
    session = _sessions.get(session_id)
    if session:
        session.permission_mode = mode
        if session.agent is not None:
            session.agent.permission_mode = mode


def get_agent_tasks() -> dict:
    return _sessions
