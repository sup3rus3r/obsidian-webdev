"""Docker container lifecycle service.

Containers are long-lived dev environments:
  - One container per project (named obsidian-webdev-{project_id})
  - Files live on a host volume mount; MongoDB is the canonical copy
  - STOP not REMOVE on idle timeout — fast restart, no re-provisioning needed
  - REMOVE only on explicit user request or 48h hard timeout

All Docker SDK calls are synchronous; wrapped with asyncio.to_thread.
"""
import asyncio
import os
import sys
from typing import AsyncGenerator, Optional

import aiofiles
import docker
import docker.errors
from fastapi import HTTPException

from config import settings
from database.mongo import get_database
from models.mongo_models import ProjectCollection, ProjectFileCollection


BASE_IMAGE = "obsidian-webdev-base:latest"

FRAMEWORK_CONFIG: dict[str, dict] = {
    "blank": {
        "image": BASE_IMAGE,
        "dev_port": 3000,
        "install_cmd": None,
        "build_cmd": None,
        "dev_cmd": None,
        "wait_for": "package.json",
    },
    "react": {
        "image": BASE_IMAGE,
        "dev_port": 5173,
        "install_cmd": "npm install",
        "build_cmd": "npm run build",
        "dev_cmd": "npm run dev -- --host --port 5173",
        "wait_for": "package.json",
    },
    "nextjs": {
        "image": BASE_IMAGE,
        "dev_port": 3000,
        "install_cmd": "npm install",
        "build_cmd": "npm run build",
        "dev_cmd": "npm run dev -- -H 0.0.0.0 -p 3000",
        "wait_for": "package.json",
    },
    "fastapi": {
        "image": BASE_IMAGE,
        "dev_port": 8000,
        "install_cmd": "uv sync",
        "build_cmd": "python -c 'import importlib; importlib.import_module(\"main\")'",
        "dev_cmd": "uvicorn main:app --host 0.0.0.0 --port 8000 --reload",
        "wait_for": "pyproject.toml",
    },
    "fullstack": {
        "image": BASE_IMAGE,
        "dev_port": 3000,
        "install_cmd": (
            "pip install uv --quiet 2>/dev/null; "
            "npm install && "
            "npm install --prefix frontend && "
            "cd backend && uv sync --quiet 2>/dev/null; cd .."
        ),
        "build_cmd": "npm run build --prefix frontend",
        "dev_cmd": "PORT=3000 npm run dev",
        "wait_for": "package.json",
    },
}


def get_docker_client() -> docker.DockerClient:
    """Return a Docker client, respecting DOCKER_SOCKET config or auto-detecting."""
    if settings.DOCKER_SOCKET:
        return docker.DockerClient(base_url=settings.DOCKER_SOCKET)
    if sys.platform == "win32":
        return docker.DockerClient(base_url="npipe:////./pipe/docker_engine")
    return docker.DockerClient(base_url="unix:///var/run/docker.sock")


def normalise_volume_path(path: str) -> str:
    """Convert a host path to Docker bind-mount format.

    On Windows with Docker Desktop, C:\\Users\\... must become /c/Users/...
    On Linux/macOS the path is returned as-is.
    """
    if sys.platform != "win32":
        return path
    drive, rest = os.path.splitdrive(path)
    if drive:
        letter = drive[0].lower()
        return f"/{letter}{rest.replace(chr(92), '/')}"
    return path.replace("\\", "/")


def _container_name(project_id: str) -> str:
    return f"obsidian-webdev-{project_id}"


def _project_dir(project_id: str) -> str:
    """Container-internal (or local dev) path — used for file I/O."""
    return os.path.join(settings.PROJECTS_DATA_DIR, project_id)


def _host_project_dir(project_id: str) -> str:
    """Host-visible path passed to Docker as a bind-mount source.

    When the backend runs inside Docker, PROJECTS_DATA_DIR is the
    container-internal path.  HOST_PROJECTS_DIR must be set to the actual
    host-side absolute path so that project containers can bind-mount it.
    For local dev (backend not containerised), these two paths are identical.
    """
    base = settings.HOST_PROJECTS_DIR or settings.PROJECTS_DATA_DIR
    return os.path.join(base, project_id)


def _get_container(client: docker.DockerClient, project_id: str):
    """Return the Docker container for a project, or None if not found."""
    try:
        return client.containers.get(_container_name(project_id))
    except docker.errors.NotFound:
        return None


def _create_container_sync(
    client: docker.DockerClient, project_id: str, framework: str
) -> docker.models.containers.Container:
    cfg = FRAMEWORK_CONFIG.get(framework, FRAMEWORK_CONFIG["blank"])

    os.makedirs(_project_dir(project_id), exist_ok=True)

    host_dir = os.path.abspath(_host_project_dir(project_id))
    vol_path = normalise_volume_path(host_dir)

    return client.containers.run(
        image=cfg["image"],
        name=_container_name(project_id),
        command="tail -f /dev/null",
        volumes={vol_path: {"bind": "/workspace", "mode": "rw"}},
        ports={
            "3000/tcp": None,
            "5173/tcp": None,
            "8000/tcp": None,
        },
        working_dir="/workspace",
        detach=True,
        labels={
            "obsidian-webdev.project_id": project_id,
            "obsidian-webdev.framework": framework,
            "obsidian-webdev.managed": "true",
        },
        mem_limit="2g",
        nano_cpus=2_000_000_000,
        auto_remove=False,
    )


def _resolve_port_sync(
    client: docker.DockerClient, container_id: str, dev_port: int
) -> Optional[int]:
    """Return the mapped host port for a container's dev server port."""
    try:
        container = client.containers.get(container_id)
        container.reload()
        mapping = container.ports.get(f"{dev_port}/tcp")
        if mapping:
            return int(mapping[0]["HostPort"])
    except (docker.errors.NotFound, KeyError, TypeError):
        pass
    return None


def _resolve_all_ports_sync(
    client: docker.DockerClient, container_id: str
) -> dict[str, int]:
    """Return all mapped host ports as {container_port_str: host_port}."""
    result: dict[str, int] = {}
    try:
        container = client.containers.get(container_id)
        container.reload()
        for port_key, mappings in container.ports.items():
            if mappings:
                port_num = port_key.split("/")[0]
                result[port_num] = int(mappings[0]["HostPort"])
    except (docker.errors.NotFound, KeyError, TypeError):
        pass
    return result


def _exec_sync(
    client: docker.DockerClient,
    container_id: str,
    cmd: str,
    workdir: str = "/workspace",
) -> tuple[int, str]:
    container = client.containers.get(container_id)
    exit_code, output = container.exec_run(
        cmd=["sh", "-c", f"umask 0000; {cmd}"],
        workdir=workdir,
        stream=False,
        demux=False,
    )
    text = output.decode("utf-8", errors="replace") if output else ""
    return exit_code, text


async def get_or_create_container(
    project_id: str, framework: str
) -> tuple[str, Optional[int], dict[str, int]]:
    """Main entry point.  Returns (docker_container_id, host_port, host_ports).

    host_port  — the host port mapped to the framework's primary dev port
    host_ports — dict of all mapped ports: {container_port_str: host_port}

    Strategy:
      1. Running container exists → return it.
      2. Stopped/paused container exists → restart it.
      3. No container → create fresh one (files already on volume if previously
         written; caller is responsible for calling restore_files_from_mongo
         when creating fresh).
    """
    cfg = FRAMEWORK_CONFIG.get(framework, FRAMEWORK_CONFIG["blank"])
    dev_port = cfg["dev_port"]

    def _work() -> tuple[str, Optional[int], dict[str, int]]:
        client = get_docker_client()
        existing = _get_container(client, project_id)

        if existing:
            status = existing.status
            if status == "running":
                existing.reload()
            elif status in ("exited", "stopped", "paused", "created"):
                existing.start()
                existing.reload()
            else:
                existing.remove(force=True)
                existing = _create_container_sync(client, project_id, framework)
        else:
            existing = _create_container_sync(client, project_id, framework)

        host_port = _resolve_port_sync(client, existing.id, dev_port)
        host_ports = _resolve_all_ports_sync(client, existing.id)
        return existing.id, host_port, host_ports

    return await asyncio.to_thread(_work)


async def restore_files_from_mongo(project_id: str) -> int:
    """Write all MongoDB file docs for a project to the host volume.

    Called when a fresh container is created so the agent has the latest
    canonical files available in /workspace.  Returns the number of files written.
    Binary files (images, fonts, etc.) are not stored in MongoDB and are skipped.
    """
    _BINARY_EXTS = frozenset({
        ".ico", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif",
        ".woff", ".woff2", ".ttf", ".otf", ".eot",
        ".mp4", ".webm", ".mp3", ".wav",
        ".pdf", ".zip", ".gz", ".tar",
        ".bin", ".exe", ".dll", ".so",
    })

    db = get_database()
    docs = await ProjectFileCollection.find_by_project(db, project_id)
    host_dir = _project_dir(project_id)

    count = 0
    for doc in docs:
        rel = doc["path"].lstrip("/")
        _, ext = os.path.splitext(rel.lower())
        if ext in _BINARY_EXTS:
            continue
        full = os.path.join(host_dir, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        async with aiofiles.open(full, "w", encoding="utf-8") as f:
            await f.write(doc.get("content", ""))
        count += 1
    return count


async def start_container(container_id: str) -> None:
    def _start():
        client = get_docker_client()
        c = client.containers.get(container_id)
        if c.status != "running":
            c.start()
    await asyncio.to_thread(_start)


async def stop_container(container_id: str) -> None:
    """Stop (not remove) a container. Volume data and MongoDB copy are preserved."""
    def _stop():
        client = get_docker_client()
        try:
            c = client.containers.get(container_id)
            if c.status == "running":
                c.stop(timeout=10)
        except docker.errors.NotFound:
            pass
    await asyncio.to_thread(_stop)


async def restart_container(container_id: str) -> None:
    def _restart():
        client = get_docker_client()
        c = client.containers.get(container_id)
        c.restart(timeout=10)
    await asyncio.to_thread(_restart)


async def remove_container(container_id: str, force: bool = False) -> None:
    """Fully remove a container. Only call on explicit request or 48h hard timeout."""
    def _remove():
        client = get_docker_client()
        try:
            c = client.containers.get(container_id)
            c.remove(force=force)
        except docker.errors.NotFound:
            pass
    await asyncio.to_thread(_remove)


async def get_container_port(project_id: str, framework: str) -> Optional[int]:
    cfg = FRAMEWORK_CONFIG.get(framework, FRAMEWORK_CONFIG["blank"])
    dev_port = cfg["dev_port"]

    def _get():
        client = get_docker_client()
        c = _get_container(client, project_id)
        if not c:
            return None
        return _resolve_port_sync(client, c.id, dev_port)

    return await asyncio.to_thread(_get)


async def exec_command(
    container_id: str,
    cmd: str,
    workdir: str = "/workspace",
) -> tuple[int, str]:
    """Run a command in a container. Returns (exit_code, output)."""
    client = get_docker_client()
    return await asyncio.to_thread(_exec_sync, client, container_id, cmd, workdir)


async def stream_exec(
    container_id: str,
    cmd: str,
    workdir: str = "/workspace",
) -> AsyncGenerator[str, None]:
    """Stream command output from a container exec (async generator)."""
    client = get_docker_client()

    def _start_exec():
        container = client.containers.get(container_id)
        exec_id = client.api.exec_create(
            container.id,
            ["sh", "-c", f"umask 0000; {cmd}"],
            workdir=workdir,
            stdout=True,
            stderr=True,
        )
        return client.api.exec_start(exec_id["Id"], stream=True)

    stream = await asyncio.to_thread(_start_exec)
    for chunk in stream:
        if isinstance(chunk, bytes):
            yield chunk.decode("utf-8", errors="replace")
        else:
            yield str(chunk)


async def start_dev_server(container_id: str, framework: str) -> None:
    """Start the framework dev server in a background tmux session.

    Uses a dedicated 'devserver' tmux session separate from the terminal's
    'workspace' session.  The command is fire-and-forget — this function returns
    as soon as tmux has created the session; npm install / server startup happen
    inside the session in the background.

    Binds to 0.0.0.0 so Docker's port mapping (host localhost:{host_port} →
    container eth0:{dev_port}) can reach the dev server.
    """
    cfg = FRAMEWORK_CONFIG.get(framework, {})
    dev_cmd = cfg.get("dev_cmd")
    if not dev_cmd:
        return

    install_cmd = cfg.get("install_cmd") or ""
    wait_for = cfg.get("wait_for", "package.json")


    wait_loop = f"while [ ! -f /workspace/{wait_for} ]; do sleep 2; done"

    log_file = "/workspace/.devserver.log"
    if install_cmd:
        inner = f"cd /workspace && {wait_loop} && {install_cmd} >> {log_file} 2>&1 && {dev_cmd} 2>&1 | tee -a {log_file}"
    else:
        inner = f"cd /workspace && {wait_loop} && {dev_cmd} 2>&1 | tee -a {log_file}"

    dev_port = cfg.get("dev_port", 3000)
    # Kill anything holding the dev port before starting fresh
    kill_port = f"fuser -k {dev_port}/tcp 2>/dev/null || true; sleep 0.5"

    cmd = (
        f"rm -f {log_file}; "
        f"{kill_port}; "
        "tmux kill-session -t devserver 2>/dev/null; "
        f"tmux new-session -d -s devserver '{inner}'"
    )
    try:
        await exec_command(container_id, cmd)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("Could not start dev server: %s", exc)


TEMPLATE_COMMANDS: dict[str, str] = {
    "nextjs": (
        "npx create-next-app@latest . "
        "--typescript --tailwind --eslint --app --no-src-dir "
        "--import-alias '@/*' --no-git --yes"
    ),
    "react": "npm create vite@latest . -- --template react-ts && npm install",
    "fastapi": (
        "pip install uv --quiet 2>/dev/null; "
        "uv init . && "
        "uv add fastapi 'uvicorn[standard]' && "
        r"printf 'from fastapi import FastAPI\n\napp = FastAPI()\n\n\n@app.get(\"/\")\ndef root():\n    return {\"message\": \"Hello World\"}\n' > main.py"
    ),
    "express": (
        "npm init -y && npm install express && "
        r"printf 'const express = require(\"express\");\n"
        r"const app = express();\n"
        r"app.get(\"/\", (req, res) => res.send(\"Hello World!\"));\n"
        r"app.listen(3000, \"0.0.0.0\");\n' > index.js"
    ),
    "fullstack": (
        "git clone --depth 1 https://github.com/sup3rus3r/nextapi.git /tmp/_tpl "
        "&& cp -r /tmp/_tpl/. /workspace/ "
        "&& rm -rf /tmp/_tpl"
    ),
}


async def inject_ssh_key(container_id: str, private_key_pem: str) -> None:
    """Write the SSH private key into ~/.ssh/id_ed25519 inside the container.

    Also writes a known_hosts-friendly ssh_config so git push/pull works
    against GitHub/GitLab without interactive host verification prompts.
    Only called when the project has an SSH key stored in the vault.
    """
    import logging
    logger = logging.getLogger(__name__)

    ssh_config = (
        "Host github.com\n"
        "  StrictHostKeyChecking no\n"
        "  UserKnownHostsFile /dev/null\n"
        "Host gitlab.com\n"
        "  StrictHostKeyChecking no\n"
        "  UserKnownHostsFile /dev/null\n"
        "Host bitbucket.org\n"
        "  StrictHostKeyChecking no\n"
        "  UserKnownHostsFile /dev/null\n"
    )

    escaped_key = private_key_pem.replace("'", "'\\''")
    escaped_config = ssh_config.replace("'", "'\\''")

    cmd = (
        "mkdir -p /root/.ssh && "
        f"printf '%s' '{escaped_key}' > /root/.ssh/id_ed25519 && "
        "chmod 600 /root/.ssh/id_ed25519 && "
        f"printf '%s' '{escaped_config}' > /root/.ssh/config && "
        "chmod 600 /root/.ssh/config"
    )

    def _run():
        client = get_docker_client()
        container = client.containers.get(container_id)
        exit_code, output = container.exec_run(
            cmd=["bash", "-c", cmd],
            user="root",
            stream=False,
            demux=False,
        )
        text = output.decode("utf-8", errors="replace") if output else ""
        return exit_code, text

    exit_code, output = await asyncio.to_thread(_run)
    if exit_code != 0:
        logger.warning("SSH key injection failed (exit %d): %s", exit_code, output)
    else:
        logger.info("SSH key injected into container %s", container_id)


async def inject_template(container_id: str, framework: str, github_url: str | None = None) -> tuple[int, str]:
    """Scaffold boilerplate by running framework CLI commands inside the container.

    Only called on first run of a brand-new project (no existing files).
    Commands can take 30-90s (npx, git clone) — always call from a background task.
    CI=1 suppresses interactive prompts in npm/npx CLIs.

    If github_url is provided (GitHub import), clones the repo instead of scaffolding.
    """
    import logging
    logger = logging.getLogger(__name__)

    if github_url:
        # Sanitise URL for shell safety (no shell expansion chars in valid git URLs)
        safe_url = github_url.replace("'", "")
        cmd = f"git clone --depth 1 '{safe_url}' ."
        is_ssh_url = github_url.startswith("git@") or github_url.startswith("ssh://")
        env = {"GIT_TERMINAL_PROMPT": "0"}
        if is_ssh_url:
            env["GIT_SSH_COMMAND"] = "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
        logger.info("Cloning repo %s into container %s (ssh=%s)", github_url, container_id, is_ssh_url)

        def _run_clone():
            client = get_docker_client()
            container = client.containers.get(container_id)
            exit_code, output = container.exec_run(
                cmd=["bash", "-c", f"umask 0000; {cmd}"],
                workdir="/workspace",
                stream=False,
                demux=False,
                environment=env,
            )
            text = output.decode("utf-8", errors="replace") if output else ""
            return exit_code, text

        return await asyncio.to_thread(_run_clone)

    cmd = TEMPLATE_COMMANDS.get(framework)
    if not cmd:
        return 0, "No template for this framework"

    logger.info("Injecting %s template into container %s", framework, container_id)

    def _run():
        client = get_docker_client()
        container = client.containers.get(container_id)
        exit_code, output = container.exec_run(
            cmd=["bash", "-c", f"umask 0000; {cmd}"],
            workdir="/workspace",
            stream=False,
            demux=False,
            environment={"CI": "1"},
        )
        text = output.decode("utf-8", errors="replace") if output else ""
        return exit_code, text

    exit_code, text = await asyncio.to_thread(_run)
    return exit_code, text


async def install_dependencies(container_id: str, framework: str) -> tuple[int, str]:
    """Run the framework-appropriate dependency install command."""
    cmd = FRAMEWORK_CONFIG.get(framework, {}).get("install_cmd")
    if not cmd:
        return 0, "No install step for this framework"
    return await exec_command(container_id, cmd)


async def run_build(container_id: str, framework: str) -> tuple[int, str]:
    """Run the framework-appropriate build command."""
    cmd = FRAMEWORK_CONFIG.get(framework, {}).get("build_cmd")
    if not cmd:
        return 0, "No build step for this framework"
    return await exec_command(container_id, cmd)


def _get_container_ip_sync(client: docker.DockerClient, container_id: str) -> str | None:
    """Return the container's first Docker bridge IP address."""
    try:
        container = client.containers.get(container_id)
        container.reload()
        networks = container.attrs.get("NetworkSettings", {}).get("Networks", {})
        for net in networks.values():
            ip = net.get("IPAddress")
            if ip:
                return ip
    except Exception:
        pass
    return None


async def probe_preview_url(
    container_id: str,
    host_ports: dict[str, int],
    timeout: float = 5.0,
) -> str | None:
    """HTTP-probe the container's dev server and return a directly-loadable URL.

    Linux/macOS: probes the container's Docker bridge IP on the standard dev port
    (5173/3000/8000).  This gives a predictable URL that matches what the dev
    server prints as its "Network" address.

    Windows (Docker Desktop): containers run inside a VM so the bridge IP is not
    reachable from the host.  Falls back to probing the host-mapped port on
    localhost instead.

    A plain TCP handshake is not enough — dev servers accept TCP connections while
    still compiling.  A minimal HTTP GET that confirms the response starts with
    "HTTP/" ensures the server is actually ready to serve content.
    """
    _PRIORITY = ["5173", "3000", "8000"]
    _CONNECT_TIMEOUT = 1.5
    _READ_TIMEOUT = 3.0

    async def _http_probe(host: str, port: int) -> bool:
        """Return True if host:port responds with an HTTP response line."""
        reader = writer = None
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=_CONNECT_TIMEOUT
            )
            writer.write(b"GET / HTTP/1.0\r\nHost: localhost\r\nConnection: close\r\n\r\n")
            await writer.drain()
            data = await asyncio.wait_for(reader.read(16), timeout=_READ_TIMEOUT)
            return data.startswith(b"HTTP")
        except Exception:
            return False
        finally:
            if writer:
                try:
                    writer.close()
                    await writer.wait_closed()
                except Exception:
                    pass

    # On Linux/macOS probe the container's bridge IP directly (no port mapping needed)
    if sys.platform != "win32":
        try:
            client = get_docker_client()
            container_ip = await asyncio.to_thread(
                _get_container_ip_sync, client, container_id
            )
        except Exception:
            container_ip = None

        if container_ip:
            results = await asyncio.gather(
                *[_http_probe(container_ip, int(p)) for p in _PRIORITY],
                return_exceptions=True,
            )
            for port_str, ok in zip(_PRIORITY, results):
                if ok is True:
                    return f"http://{container_ip}:{port_str}"

    # On Windows (Docker Desktop) — or Linux fallback — probe via host-mapped ports.
    # Always do a fresh live lookup from Docker so we never use stale DB values.
    try:
        client = get_docker_client()
        live_ports: dict[str, int] = await asyncio.to_thread(
            _resolve_all_ports_sync, client, container_id
        )
    except Exception:
        live_ports = {}

    # Merge: live ports take priority; fall back to DB-stored host_ports
    merged: dict[str, int] = {**host_ports, **live_ports}
    logger.info("probe_preview_url: container=%s live_ports=%s merged=%s", container_id[:12], live_ports, merged)

    candidates: list[tuple[str, int]] = []
    for p in _PRIORITY:
        if p in merged:
            candidates.append((p, merged[p]))
    for p, hp in merged.items():
        if p not in _PRIORITY:
            candidates.append((p, hp))

    if not candidates:
        logger.info("probe_preview_url: no candidates — port mapping missing")
        return None

    logger.info("probe_preview_url: probing candidates=%s", candidates)
    results = await asyncio.gather(
        *[_http_probe("127.0.0.1", hp) for _, hp in candidates],
        return_exceptions=True,
    )
    for (cport, _), ok in zip(candidates, results):
        logger.info("probe_preview_url: 127.0.0.1:%s -> %s", merged[cport], ok)
        if ok is True:
            host_port = merged[cport]
            return f"http://localhost:{host_port}"

    return None


async def container_cleanup_task() -> None:
    """Background task: auto-stop idle containers; hard-remove expired ones.

    Runs every 5 minutes. Uses project.updated_at as last-activity proxy.
    Idle threshold:  CONTAINER_IDLE_TIMEOUT_MINUTES (default 30)
    Hard-remove:     CONTAINER_HARD_REMOVE_HOURS    (default 48)
    """
    from datetime import datetime, timedelta, timezone

    idle_td = timedelta(minutes=settings.CONTAINER_IDLE_TIMEOUT_MINUTES)
    remove_td = timedelta(hours=settings.CONTAINER_HARD_REMOVE_HOURS)

    while True:
        await asyncio.sleep(300)
        try:
            db = get_database()
            cursor = db["projects"].find(
                {"status": {"$in": ["running", "stopped"]}, "container_id": {"$ne": None}}
            )
            docs = await cursor.to_list(length=200)
            now = datetime.now(timezone.utc)

            for doc in docs:
                project_id = str(doc["_id"])
                container_id = doc.get("container_id")
                last_active = doc.get("updated_at") or doc.get("created_at")

                if not container_id or not last_active:
                    continue

                idle = now - last_active

                if idle > remove_td:
                    await remove_container(container_id, force=True)
                    await db["projects"].update_one(
                        {"_id": doc["_id"]},
                        {"$set": {
                            "status": "stopped",
                            "container_id": None,
                            "host_port": None,
                            "updated_at": now,
                        }},
                    )
                elif idle > idle_td and doc.get("status") == "running":
                    await stop_container(container_id)
                    await db["projects"].update_one(
                        {"_id": doc["_id"]},
                        {"$set": {"status": "stopped", "updated_at": now}},
                    )
        except Exception:
            pass
