"""Terminal WebSocket — bridges xterm.js ↔ a shell inside the project container.

Auth:  JWT passed as ?token=<access_token> query parameter.

Protocol (client → server):
  - Binary frames  → raw bytes sent to container stdin (keystrokes)
  - Text frames    → JSON control message, currently only resize:
                     {"type": "resize", "cols": 120, "rows": 40}

Protocol (server → client):
  - Binary frames  → raw bytes from container stdout/stderr

On Linux/macOS a PTY is allocated so colors, cursor keys, and PS1 prompts work
correctly with xterm.js.  On Windows a PIPE fallback is used (no color support).

Close codes:
  4001 — unauthorized
  4004 — project not found or not owned by the authenticated user
  4009 — no active container for this project (start one via POST /containers/{id}/start)
"""
import asyncio
import json
import logging
import os
import struct
import sys
from typing import Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

from config import settings
from core.security import TokenData
from database.mongo import get_database
from models.mongo_models import ProjectCollection
from websocket.manager import terminal_manager

logger = logging.getLogger(__name__)
router = APIRouter()

_USE_PTY = sys.platform != "win32"


def _auth_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("token_type") != "user":
            raise ValueError("Invalid token type")
        return TokenData(
            user_id=payload["user_id"],
            username=payload["username"],
            role=payload.get("role", "guest"),
        )
    except JWTError as exc:
        raise ValueError(str(exc)) from exc


def _resize_pty(master_fd: int, cols: int, rows: int) -> None:
    """Send TIOCSWINSZ to resize the container PTY (Linux/macOS only)."""
    import fcntl
    import termios
    fcntl.ioctl(
        master_fd,
        termios.TIOCSWINSZ,
        struct.pack("HHHH", rows, cols, 0, 0),
    )


async def _bridge_pty(websocket: WebSocket, container_id: str) -> None:
    """PTY-backed bridge (Linux/macOS) using tmux for persistent sessions.

    - A pseudo-terminal pair is allocated on the host.
    - The slave fd is passed to `docker exec` which runs `tmux new-session -A`.
    - tmux runs as a server inside the container — detaching (WS disconnect)
      does NOT kill running processes (e.g. npm run dev / uvicorn).
    - On reconnect the same tmux session is re-attached, restoring history.
    """
    master_fd, slave_fd = os.openpty()


    _resize_pty(master_fd, 220, 50)
    try:
        shell_cmd = (
            "which tmux > /dev/null 2>&1 "
            "|| apk add -q --no-cache tmux 2>/dev/null "
            "|| (apt-get update -qq && apt-get install -yq tmux) 2>/dev/null; "
            "tmux new-session -d -s workspace 2>/dev/null; "
            "tmux set -g status off; "
            "tmux attach-session -t workspace"
        )
        proc = await asyncio.create_subprocess_exec(
            "docker", "exec", "-it", "-e", "TERM=xterm-256color", container_id, "/bin/sh", "-c", shell_cmd,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
        )
        os.close(slave_fd)

        loop = asyncio.get_event_loop()

        async def _read_output() -> None:
            while True:
                try:
                    chunk = await loop.run_in_executor(
                        None, os.read, master_fd, 4096
                    )
                    if not chunk:
                        break
                    await websocket.send_bytes(chunk)
                except (OSError, WebSocketDisconnect):
                    break

        async def _write_input() -> None:
            while True:
                try:
                    frame = await websocket.receive()
                    if frame.get("type") == "websocket.disconnect":
                        break
                    if "bytes" in frame:
                        os.write(master_fd, frame["bytes"])
                    elif "text" in frame:
                        try:
                            ctrl = json.loads(frame["text"])
                            if ctrl.get("type") == "resize":
                                _resize_pty(
                                    master_fd,
                                    int(ctrl.get("cols", 80)),
                                    int(ctrl.get("rows", 24)),
                                )
                        except (json.JSONDecodeError, KeyError, ValueError):
                            pass
                except (OSError, WebSocketDisconnect, RuntimeError):
                    break

        tasks = [
            asyncio.create_task(_read_output()),
            asyncio.create_task(_write_input()),
        ]
        _done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for t in pending:
            t.cancel()


    finally:
        try:
            os.close(master_fd)
        except OSError:
            pass


async def _bridge_pipe(websocket: WebSocket, container_id: str) -> None:
    """PIPE-backed bridge (Windows fallback — no PTY, no colors).

    Basic stdin/stdout piping without PTY allocation.
    Shell input/output works but colour codes and cursor keys are not emulated.
    """
    proc = await asyncio.create_subprocess_exec(
        "docker", "exec", "-i", container_id, "/bin/sh",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    async def _read_output() -> None:
        while True:
            try:
                chunk = await proc.stdout.read(4096)
                if not chunk:
                    break
                await websocket.send_bytes(chunk)
            except (OSError, WebSocketDisconnect):
                break

    async def _write_input() -> None:
        while True:
            try:
                frame = await websocket.receive()
                if frame.get("type") == "websocket.disconnect":
                    break
                if "bytes" in frame:
                    proc.stdin.write(frame["bytes"])
                    await proc.stdin.drain()
            except (OSError, WebSocketDisconnect, RuntimeError):
                break

    tasks = [
        asyncio.create_task(_read_output()),
        asyncio.create_task(_write_input()),
    ]
    _done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    for t in pending:
        t.cancel()

    if proc.returncode is None:
        proc.terminate()


@router.websocket("/ws/terminal/{project_id}")
async def terminal_ws(
    websocket: WebSocket,
    project_id: str,
    token: str = Query(...),
):
    """Bidirectional terminal bridge between xterm.js and the project container."""
    try:
        user = _auth_token(token)
    except ValueError:
        await websocket.accept()
        await websocket.close(code=4001, reason="Unauthorized")
        return

    db = get_database()
    project = await ProjectCollection.find_by_id(db, project_id)
    if not project or project.get("owner_id") != user.user_id:
        await websocket.accept()
        await websocket.close(code=4004, reason="Project not found")
        return

    container_id = project.get("container_id")
    if not container_id:
        await websocket.accept()
        await websocket.close(code=4009, reason="No active container")
        return

    await terminal_manager.connect(project_id, websocket)
    try:
        if _USE_PTY:
            await _bridge_pty(websocket, container_id)
        else:
            await _bridge_pipe(websocket, container_id)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Terminal WS error for project %s", project_id)
    finally:
        terminal_manager.disconnect(project_id, websocket)
