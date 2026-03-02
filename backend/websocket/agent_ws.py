"""Agent WebSocket endpoint — single ReAct agent, simplified.

Auth: JWT passed as ?token=<access_token> query parameter.

Client → Server messages:
  {"type": "chat", "content": "...", "model_provider": "...", "model_id": "..."}
  {"type": "stop"}
  {"type": "tool_approval_response", "approval_id": "...", "approved": true/false}
  {"type": "clarification_response", "clarification_id": "...", "answer": "..."}
  {"type": "set_permission_mode", "mode": "ask"|"auto"}

Server → Client events:
  {"type": "connected", "status": "idle"|"running"}
  {"type": "token", "content": "..."}
  {"type": "tool_call", "tool": "...", "params": {...}}
  {"type": "tool_result", "tool": "...", "result": "..."}
  {"type": "tool_approval_request", "approval_id": "...", "tool": "...", "params": {...}}
  {"type": "clarification_request", "clarification_id": "...", "question": "..."}
  {"type": "compacting"}
  {"type": "done", "content": "..."}
  {"type": "stopped"}
  {"type": "error", "message": "..."}
"""
import json
import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

from config import settings
from core.security import TokenData
from database.mongo import get_database
from models.mongo_models import AgentSessionCollection, ProjectCollection
import services.agent_runner as runner
from websocket.manager import agent_manager

logger = logging.getLogger(__name__)
router = APIRouter()


def _auth_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("token_type") != "user":
            raise ValueError("Invalid token type")
        return TokenData(
            user_id=payload["user_id"],
            username=payload["username"],
            role=payload.get("role", "guest"),
        )
    except JWTError as exc:
        raise ValueError(str(exc)) from exc


async def _get_api_key(db, user_id: str, model_provider: str) -> str:
    """Retrieve the user's API key for the provider from the vault, falling back to env vars."""
    try:
        from models.mongo_models import UserSecretCollection
        from core.vault import decrypt_secret
        secret = await UserSecretCollection.find_by_provider(db, user_id, model_provider)
        if secret:
            return decrypt_secret(user_id, secret["encrypted_value"], secret.get("key_version", 1))
    except Exception:
        pass
    env_map = {
        "anthropic": settings.ANTHROPIC_API_KEY,
        "openai":    settings.OPENAI_API_KEY,
    }
    return env_map.get(model_provider, "")


@router.websocket("/ws/agent/{session_id}")
async def agent_ws(
    websocket: WebSocket,
    session_id: str,
    token: str = Query(...),
):
    try:
        user = _auth_token(token)
    except ValueError:
        await websocket.accept()
        await websocket.close(code=4001, reason="Unauthorized")
        return

    db = get_database()
    session_doc = await AgentSessionCollection.find_by_id(db, session_id)
    if not session_doc or session_doc.get("user_id") != user.user_id:
        await websocket.accept()
        await websocket.close(code=4004, reason="Session not found")
        return

    await agent_manager.connect(session_id, websocket)

    async def send_event(event: dict) -> None:
        try:
            await agent_manager.send_json(session_id, event)
        except Exception:
            pass

    try:
        await send_event({"type": "connected", "status": session_doc.get("status", "idle")})


        project_id = session_doc.get("project_id")
        display_history = await runner.get_display_history(project_id)
        if display_history:
            await send_event({"type": "history", "messages": display_history})

        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await send_event({"type": "error", "message": "Invalid JSON"})
                continue

            msg_type = msg.get("type")

            if msg_type == "chat":
                content = msg.get("content", "").strip()
                if not content:
                    await send_event({"type": "error", "message": "chat.content must not be empty"})
                    continue


                session_doc = await AgentSessionCollection.find_by_id(db, session_id)
                project_id = session_doc.get("project_id")
                project = await ProjectCollection.find_by_id(db, project_id)
                if not project:
                    await send_event({"type": "error", "message": "Project not found"})
                    continue

                container_id = project.get("container_id")
                if not container_id:
                    await send_event({
                        "type": "error",
                        "message": "Container is not running. Start the container first.",
                    })
                    continue

                model_provider = (
                    msg.get("model_provider")
                    or session_doc.get("model_provider", "openai")
                )
                model_id = (
                    msg.get("model_id")
                    or session_doc.get("model_id", "gpt-4.1")
                )
                api_key = await _get_api_key(db, user.user_id, model_provider)

                from models.mongo_models import UserPreferencesCollection
                prefs = await UserPreferencesCollection.get_or_default(db, user.user_id)

                await runner.start_agent(
                    session_id=session_id,
                    prompt=content,
                    project_name=project.get("name", "Project"),
                    framework=project.get("framework", "blank"),
                    send_event=send_event,
                    project_id=project_id,
                    container_id=container_id,
                    model_provider=model_provider,
                    model_id=model_id,
                    api_key=api_key,
                    permission_mode=prefs["permission_mode"],
                    max_bash_lines=prefs["max_bash_lines"],
                    max_file_lines=prefs["max_file_lines"],
                    max_web_chars=prefs["max_web_chars"],
                    compact_threshold=prefs["compact_threshold"],
                )

            elif msg_type == "stop":
                await runner.stop_agent(session_id)

            elif msg_type == "tool_approval_response":
                approval_id = msg.get("approval_id")
                approved = bool(msg.get("approved", False))
                if approval_id:
                    runner.resolve_approval(session_id, approval_id, approved)
                else:
                    await send_event({
                        "type": "error",
                        "message": "tool_approval_response missing approval_id",
                    })

            elif msg_type == "clarification_response":
                clarification_id = msg.get("clarification_id")
                answer = msg.get("answer", "")
                if clarification_id:
                    runner.resolve_clarification(session_id, clarification_id, answer)
                else:
                    await send_event({
                        "type": "error",
                        "message": "clarification_response missing clarification_id",
                    })

            elif msg_type == "set_permission_mode":
                mode = msg.get("mode")
                if mode in ("ask", "auto"):
                    runner.set_permission_mode(session_id, mode)
                else:
                    await send_event({
                        "type": "error",
                        "message": f"Invalid permission mode: {mode!r}. Use 'ask' or 'auto'.",
                    })

            elif msg_type == "clear_history":
                await runner.clear_conversation(session_doc.get("project_id", ""))
                await send_event({"type": "history", "messages": []})

            else:
                await send_event({
                    "type": "error",
                    "message": f"Unknown message type: {msg_type!r}",
                })

    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Unexpected error in agent WS session %s", session_id)
        try:
            await send_event({"type": "error", "message": "Internal server error"})
        except Exception:
            pass
    finally:
        runner.remove_session(session_id)
        agent_manager.disconnect(session_id, websocket)
