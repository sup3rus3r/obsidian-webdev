"""Single ReAct agent — Claude Code-style tool loop.

Supports Anthropic, OpenAI, Ollama (OpenAI-compat), and LMStudio (OpenAI-compat).

The agent runs a loop:
  1. Call LLM (streaming → emit token events)
  2. Parse tool calls from response
  3. For each tool call: check permission → (ask approval) → execute → emit result
  4. Append assistant turn + tool results to message history
  5. Repeat until no tool calls (task done) or stop_event is set
"""
from __future__ import annotations

import asyncio
import glob as _glob
import json
import logging
import os
import re
from html.parser import HTMLParser
from typing import Awaitable, Callable
from uuid import uuid4

import aiofiles
import httpx

from agents.tools import TOOLS_ANTHROPIC, TOOLS_OPENAI, tool_tier
from config import settings
from database.mongo import get_database
from models.mongo_models import ProjectFileCollection, ProjectFileSummaryCollection
from services.container_service import exec_command

logger = logging.getLogger(__name__)


_CONTEXT_LIMITS: dict[str, int] = {
    "claude-opus-4-6": 200_000,
    "claude-sonnet-4-6": 200_000,
    "claude-haiku-4-5-20251001": 200_000,
    "gpt-4.1": 1_000_000,
    "gpt-4.1-mini": 1_000_000,
    "o3": 200_000,
    "o4-mini": 200_000,
}
_DEFAULT_LOCAL_LIMIT = 32_000
_PRUNE_THRESHOLD = 0.60
_COMPACT_THRESHOLD = 0.80
_COMPACT_KEEP_RECENT = 8
_PRUNE_KEEP_RECENT = 10
_PRUNE_RESULT_MAX = 500
_MAX_BASH_LINES = 400
_MAX_FILE_LINES = 500
_MAX_WEB_CHARS = 20_000
_MAX_ITERATIONS = None  # No cap — run until the model declares done or user stops


def _load_system_prompt() -> str:
    path = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "AGENT_SYSTEM_PROMPT.md")
    try:
        with open(path) as fh:
            content = fh.read()
        m = re.search(r"```\n(.*?)\n```", content, re.DOTALL)
        return m.group(1) if m else content
    except FileNotFoundError:
        return (
            "You are an expert full-stack software engineer AI inside a Docker container. "
            "Work in a loop: reason, call a tool, observe, repeat until done."
        )


_SYSTEM_PROMPT_TEMPLATE = _load_system_prompt()


class _StripHTML(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def get_text(self) -> str:
        return " ".join(self._parts)


def _strip_html(html: str) -> str:
    p = _StripHTML()
    p.feed(html)
    return p.get_text()


class Agent:
    """Single ReAct agent.

    on_event         — async(event_dict) — streams events to the WS client
    request_approval — async(approval_id, tool_name, params) → bool
                       suspends until the user approves or denies the tool call
    """

    def __init__(
        self,
        *,
        project_id: str,
        container_id: str,
        project_name: str,
        framework: str,
        model_provider: str,
        model_id: str,
        api_key: str,
        on_event: Callable[[dict], Awaitable[None]],
        request_approval: Callable[[str, str, dict], Awaitable[bool]],
        request_clarification: Callable[[str, str], Awaitable[str]],
        permission_mode: str = "ask",
        max_bash_lines: int = _MAX_BASH_LINES,
        max_file_lines: int = _MAX_FILE_LINES,
        max_web_chars: int = _MAX_WEB_CHARS,
        compact_threshold: float = _COMPACT_THRESHOLD,
    ) -> None:
        self.project_id = project_id
        self.container_id = container_id
        self.project_name = project_name
        self.framework = framework
        self.model_provider = model_provider
        self.model_id = model_id
        self.api_key = api_key
        self.on_event = on_event
        self.request_approval = request_approval
        self.request_clarification = request_clarification
        self.permission_mode = permission_mode
        self.max_bash_lines = max_bash_lines
        self.max_file_lines = max_file_lines
        self.max_web_chars = max_web_chars
        self.compact_threshold = compact_threshold
        self._context_limit = _CONTEXT_LIMITS.get(model_id, _DEFAULT_LOCAL_LIMIT)
        self._last_input_tokens: int = 0
        self._system_prompt = (
            _SYSTEM_PROMPT_TEMPLATE
            .replace("{{project_name}}", project_name)
            .replace("{{framework}}", framework)
        )
        self._host_workspace = os.path.join(settings.PROJECTS_DATA_DIR, project_id)


    async def run(
        self,
        prompt: str,
        messages: list[dict],
        stop_event: asyncio.Event,
    ) -> None:
        """Run the ReAct loop.

        prompt   — the new user message
        messages — conversation history (mutated in-place)
        """
        messages.append({"role": "user", "content": prompt})

        import itertools
        for _ in itertools.count() if _MAX_ITERATIONS is None else range(_MAX_ITERATIONS):
            if stop_event.is_set():
                await self.on_event({"type": "stopped"})
                return

            tokens = self._estimate_tokens(messages)
            if tokens > self._context_limit * self.compact_threshold:
                await self._compact(messages)
                if stop_event.is_set():
                    await self.on_event({"type": "stopped"})
                    return
            elif tokens > self._context_limit * _PRUNE_THRESHOLD:
                self._prune_old_tool_results(messages)
                self._last_input_tokens = 0

            try:
                response = await self._llm_call(messages)
            except Exception as exc:
                logger.exception("LLM call failed")
                detail = str(exc)
                if hasattr(exc, "__cause__") and exc.__cause__:
                    detail = f"{exc} — {exc.__cause__}"
                # Strip HTML error pages (e.g. LM Studio 500 responses) to just the text
                if "<html" in detail.lower() or "<!doctype" in detail.lower():
                    detail = _strip_html(detail).strip() or detail[:200]
                # Add resolved URL for local providers to aid debugging
                if self.model_provider in ("ollama", "lmstudio"):
                    try:
                        resolved_url, _ = self._resolve_local_client(self.model_provider)
                        detail = f"{detail} (URL: {resolved_url})"
                    except Exception:
                        pass
                await self.on_event({"type": "error", "message": f"LLM error: {detail}"})
                return

            if self.model_provider == "anthropic":
                done = await self._process_anthropic(response, messages, stop_event)
            else:
                done = await self._process_openai(response, messages, stop_event)

            if done or stop_event.is_set():
                return

        # Unreachable when _MAX_ITERATIONS is None — loop only exits via return above


    async def _llm_call(self, messages: list[dict]) -> dict:
        if self.model_provider == "anthropic":
            result = await self._call_anthropic(messages)
        else:
            result = await self._call_openai(messages)
        if result.get("input_tokens"):
            self._last_input_tokens = result["input_tokens"]
        return result

    async def _call_anthropic(self, messages: list[dict]) -> dict:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=self.api_key or settings.ANTHROPIC_API_KEY)
        async with client.messages.stream(
            model=self.model_id,
            max_tokens=8192,
            system=self._system_prompt,
            messages=messages,
            tools=TOOLS_ANTHROPIC,
        ) as stream:
            async for text in stream.text_stream:
                await self.on_event({"type": "token", "content": text})
            msg = await stream.get_final_message()
        return {
            "provider": "anthropic",
            "message": msg,
            "input_tokens": msg.usage.input_tokens,
        }

    def _resolve_local_client(self, provider: str):
        """Return (base_url, api_key) for a local provider, reading from vault via self.api_key."""
        from services.vault_service import _parse_local_value

        def _normalize(url: str) -> str:
            """Strip trailing /v1 or / then append /v1 — handles any suffix cleanly."""
            url = url.rstrip("/")
            if url.endswith("/v1"):
                url = url[:-3]
            return f"{url}/v1"

        vault_url, vault_key = _parse_local_value(self.api_key) if self.api_key else ("", "")
        if provider == "ollama":
            base_url = _normalize(vault_url or settings.OLLAMA_BASE_URL)
            api_key = vault_key or "ollama"
        else:  # lmstudio
            base_url = _normalize(vault_url or settings.LMSTUDIO_BASE_URL)
            api_key = vault_key or "lmstudio"
        logger.debug("Local provider %s → base_url=%s", provider, base_url)
        return base_url, api_key

    async def _call_openai(self, messages: list[dict]) -> dict:
        import openai
        base_url: str | None = None
        api_key = self.api_key or settings.OPENAI_API_KEY
        if self.model_provider in ("ollama", "lmstudio"):
            base_url, api_key = self._resolve_local_client(self.model_provider)
        client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
        oai_messages = [{"role": "system", "content": self._system_prompt}, *messages]
        is_reasoning = self.model_id.startswith(("o1", "o3", "o4"))
        text_buf = ""
        tool_calls_buf: dict[int, dict] = {}
        finish_reason: str | None = None

        input_tokens = 0
        if is_reasoning:
            resp = await client.chat.completions.create(
                model=self.model_id,
                messages=oai_messages,
                tools=TOOLS_OPENAI,
                max_completion_tokens=8192,
            )
            choice = resp.choices[0]
            finish_reason = choice.finish_reason
            if choice.message.content:
                text_buf = choice.message.content
                await self.on_event({"type": "token", "content": text_buf})
            for i, tc in enumerate(choice.message.tool_calls or []):
                tool_calls_buf[i] = {
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                }
            if resp.usage:
                input_tokens = resp.usage.prompt_tokens
        else:
            stream_kwargs: dict = {}
            if self.model_provider == "openai":
                stream_kwargs["stream_options"] = {"include_usage": True}
            stream = await client.chat.completions.create(
                model=self.model_id,
                messages=oai_messages,
                tools=TOOLS_OPENAI,
                stream=True,
                max_tokens=8192,
                **stream_kwargs,
            )
            async for chunk in stream:
                if chunk.usage:
                    input_tokens = chunk.usage.prompt_tokens
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if chunk.choices[0].finish_reason:
                    finish_reason = chunk.choices[0].finish_reason
                if delta.content:
                    text_buf += delta.content
                    await self.on_event({"type": "token", "content": delta.content})
                for tc in delta.tool_calls or []:
                    idx = tc.index
                    if idx not in tool_calls_buf:
                        tool_calls_buf[idx] = {"id": "", "name": "", "arguments": ""}
                    if tc.id:
                        tool_calls_buf[idx]["id"] = tc.id
                    if tc.function.name:
                        tool_calls_buf[idx]["name"] = tc.function.name
                    if tc.function.arguments:
                        tool_calls_buf[idx]["arguments"] += tc.function.arguments

        return {
            "provider": "openai",
            "text": text_buf,
            "tool_calls": list(tool_calls_buf.values()),
            "finish_reason": finish_reason,
            "input_tokens": input_tokens,
        }


    async def _process_anthropic(
        self,
        response: dict,
        messages: list[dict],
        stop_event: asyncio.Event,
    ) -> bool:
        """Append assistant turn, execute tools in parallel, append results. Returns True if done."""
        msg = response["message"]
        text = "".join(b.text for b in msg.content if b.type == "text")
        tool_calls = [
            {"id": b.id, "name": b.name, "params": b.input}
            for b in msg.content
            if b.type == "tool_use"
        ]
        messages.append({"role": "assistant", "content": [
            {k: v for k, v in b.model_dump().items() if v is not None}
            for b in msg.content
        ]})

        if not tool_calls:
            await self.on_event({"type": "done", "content": text})
            return True


        result_map: dict[str, str] = {tc["id"]: "Interrupted." for tc in tool_calls}

        async def _run_one(tc: dict) -> None:
            if stop_event.is_set():
                return
            try:
                result_map[tc["id"]] = await self._handle_tool_call(tc, stop_event)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                result_map[tc["id"]] = f"Error: {exc}"

        cancelled = False
        try:
            await asyncio.gather(*[_run_one(tc) for tc in tool_calls])
        except asyncio.CancelledError:
            cancelled = True

        messages.append({
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": tc["id"], "content": result_map[tc["id"]]}
                for tc in tool_calls
            ],
        })
        if cancelled:
            raise asyncio.CancelledError
        if stop_event.is_set():
            await self.on_event({"type": "stopped"})
            return True
        return False

    async def _process_openai(
        self,
        response: dict,
        messages: list[dict],
        stop_event: asyncio.Event,
    ) -> bool:
        """Append assistant turn, execute tools in parallel, append results. Returns True if done."""
        text = response.get("text", "")
        raw_tcs = response.get("tool_calls", [])
        finish_reason = response.get("finish_reason")

        assistant_msg: dict = {"role": "assistant"}
        if text:
            assistant_msg["content"] = text
        if raw_tcs:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {"name": tc["name"], "arguments": tc["arguments"]},
                }
                for tc in raw_tcs
            ]
        messages.append(assistant_msg)

        if not raw_tcs or finish_reason == "stop":
            await self.on_event({"type": "done", "content": text})
            return True

        result_map: dict[str, str] = {tc["id"]: "Interrupted." for tc in raw_tcs}

        async def _run_one(tc: dict) -> None:
            if stop_event.is_set():
                return
            try:
                params = json.loads(tc["arguments"])
            except (json.JSONDecodeError, KeyError):
                params = {}
            normalized = {"id": tc["id"], "name": tc["name"], "params": params}
            try:
                result_map[tc["id"]] = await self._handle_tool_call(normalized, stop_event)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                result_map[tc["id"]] = f"Error: {exc}"

        cancelled = False
        try:
            await asyncio.gather(*[_run_one(tc) for tc in raw_tcs])
        except asyncio.CancelledError:
            cancelled = True

        for tc in raw_tcs:
            messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result_map[tc["id"]]})

        if cancelled:
            raise asyncio.CancelledError
        if stop_event.is_set():
            await self.on_event({"type": "stopped"})
            return True
        return False


    async def _handle_tool_call(
        self,
        tc: dict,
        stop_event: asyncio.Event,
    ) -> str:
        name = tc["name"]
        params = tc["params"]


        if name == "ask_user":
            result = await self._ask_user(params.get("question", ""))
            await self.on_event({"type": "tool_result", "tool": name, "result": result})
            return result

        tier = tool_tier(name, params)
        needs_approval = tier == "always" or (tier == "ask" and self.permission_mode == "ask")

        if needs_approval:
            approval_id = str(uuid4())
            await self.on_event({
                "type": "tool_approval_request",
                "approval_id": approval_id,
                "tool": name,
                "params": params,
            })
            try:
                approved = await asyncio.wait_for(
                    self.request_approval(approval_id, name, params),
                    timeout=300,
                )
            except asyncio.TimeoutError:
                approved = False
            if not approved:
                result = f"Tool `{name}` was denied by the user."
                await self.on_event({
                    "type": "tool_result",
                    "tool": name,
                    "result": result,
                    "denied": True,
                })
                return result

        await self.on_event({"type": "tool_call", "tool": name, "params": params})
        result = await self._execute_tool(name, params)
        await self.on_event({"type": "tool_result", "tool": name, "result": result})
        return result

    async def _execute_tool(self, name: str, params: dict) -> str:
        dispatch = {
            "read_file":        self._read_file,
            "write_file":       self._write_file,
            "edit_file":        self._edit_file,
            "bash":             self._bash,
            "glob":             self._glob,
            "grep":             self._grep,
            "web_fetch":        self._web_fetch,
            "web_search":       self._web_search,
            "list_files_brief": self._list_files_brief,
        }
        fn = dispatch.get(name)
        if not fn:
            return f"Error: unknown tool '{name}'"
        try:
            return await fn(**params)
        except TypeError as exc:
            return f"Error: bad parameters for {name}: {exc}"
        except Exception as exc:
            logger.exception("Tool %s raised an exception", name)
            return f"Error: {exc}"


    def _resolve_path(self, path: str) -> str:
        """Resolve a /workspace/... or relative path to a host FS absolute path."""
        if path.startswith("/workspace"):
            rel = path[len("/workspace"):].lstrip("/")
        else:
            rel = path.lstrip("/")
        return os.path.join(self._host_workspace, rel)

    async def _read_file(self, path: str) -> str:
        host_path = self._resolve_path(path)
        try:
            async with aiofiles.open(host_path, "r", encoding="utf-8", errors="replace") as f:
                content = await f.read()
        except FileNotFoundError:
            return f"Error: File not found: {path}"
        except PermissionError:
            return f"Error: Permission denied: {path}"
        lines = content.splitlines()
        if len(lines) > self.max_file_lines:
            half = self.max_file_lines // 2
            mid = len(lines) - self.max_file_lines
            lines = lines[:half] + [f"... [{mid} lines truncated] ..."] + lines[-half:]
            content = "\n".join(lines)
        return content

    async def _write_file(self, path: str, content: str) -> str:
        host_path = self._resolve_path(path)
        os.makedirs(os.path.dirname(host_path), exist_ok=True)
        async with aiofiles.open(host_path, "w", encoding="utf-8") as f:
            await f.write(content)
        rel = os.path.relpath(host_path, self._host_workspace)
        db = get_database()
        await ProjectFileCollection.upsert(db, self.project_id, rel, content)
        await self.on_event({"type": "file_changed", "path": f"/workspace/{rel}"})
        if len(content) > 100:
            asyncio.create_task(self._update_file_summary(rel, content))
        return f"Written: {path}"

    async def _edit_file(self, path: str, old_string: str, new_string: str) -> str:
        host_path = self._resolve_path(path)
        try:
            async with aiofiles.open(host_path, "r", encoding="utf-8") as f:
                content = await f.read()
        except FileNotFoundError:
            return f"Error: File not found: {path}"
        count = content.count(old_string)
        if count == 0:
            return f"Error: old_string not found in {path}"
        if count > 1:
            return f"Error: old_string found {count} times — must be unique. Add more surrounding context."
        new_content = content.replace(old_string, new_string, 1)
        async with aiofiles.open(host_path, "w", encoding="utf-8") as f:
            await f.write(new_content)
        rel = os.path.relpath(host_path, self._host_workspace)
        db = get_database()
        await ProjectFileCollection.upsert(db, self.project_id, rel, new_content)
        await self.on_event({"type": "file_changed", "path": f"/workspace/{rel}"})
        if len(new_content) > 100:
            asyncio.create_task(self._update_file_summary(rel, new_content))
        return f"Edited: {path}"

    async def _bash(self, command: str) -> str:
        exit_code, output = await exec_command(self.container_id, command)
        lines = output.splitlines()
        half = self.max_bash_lines // 2
        if len(lines) > self.max_bash_lines:
            mid = len(lines) - self.max_bash_lines
            lines = lines[:half] + [f"... [{mid} lines truncated] ..."] + lines[-half:]
        body = "\n".join(lines)
        return f"Exit: {exit_code}\n{body}" if body else f"Exit: {exit_code}"

    async def _glob(self, pattern: str) -> str:
        full = os.path.join(self._host_workspace, pattern)
        matches = sorted(_glob.glob(full, recursive=True))
        if not matches:
            return "No matches found."
        results = [
            f"/workspace/{os.path.relpath(m, self._host_workspace)}"
            for m in matches[:200]
        ]
        suffix = f"\n(showing 200 of {len(matches)} matches)" if len(matches) > 200 else ""
        return "\n".join(results) + suffix

    async def _grep(self, pattern: str, path: str = ".", options: str = "") -> str:
        if not path.startswith("/workspace"):
            path = f"/workspace/{path.lstrip('/')}"
        opts = options.strip() if options.strip() else "-rn"
        safe_pattern = pattern.replace("'", r"'\''")
        cmd = f"grep {opts} '{safe_pattern}' '{path}' 2>/dev/null | head -200"
        _, output = await exec_command(self.container_id, cmd)
        return output if output.strip() else "No matches found."

    async def _web_fetch(self, url: str) -> str:
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                content_type = resp.headers.get("content-type", "")
                text = _strip_html(resp.text) if "html" in content_type else resp.text
        except Exception as exc:
            return f"Error fetching {url}: {exc}"
        if len(text) > self.max_web_chars:
            text = text[: self.max_web_chars] + f"\n... [truncated at {self.max_web_chars} chars]"
        return text

    async def _web_search(self, query: str) -> str:
        if settings.TAVILY_API_KEY:
            try:
                from tavily import TavilyClient
                client = TavilyClient(api_key=settings.TAVILY_API_KEY)
                result = await asyncio.to_thread(
                    client.search, query, max_results=5, search_depth="basic"
                )
                parts = [
                    f"### {r.get('title', '')}\n{r.get('url', '')}\n{r.get('content', '')}"
                    for r in result.get("results", [])
                ]
                return "\n\n".join(parts) or "No results."
            except Exception as exc:
                logger.warning("Tavily search failed: %s", exc)
        try:
            from duckduckgo_search import DDGS
            results = await asyncio.to_thread(
                lambda: list(DDGS().text(query, max_results=5))
            )
            parts = [
                f"### {r.get('title', '')}\n{r.get('href', '')}\n{r.get('body', '')}"
                for r in results
            ]
            return "\n\n".join(parts) or "No results."
        except Exception as exc:
            return f"Web search unavailable: {exc}"


    def _estimate_tokens(self, messages: list[dict]) -> int:
        """Use actual input token count from the last LLM response when available,
        falling back to a character-based estimate for the first call or after reset."""
        if self._last_input_tokens > 0:
            return self._last_input_tokens
        try:
            return len(json.dumps(messages, default=str)) // 4
        except Exception:
            return 0

    def _prune_old_tool_results(self, messages: list[dict]) -> None:
        """Truncate verbose tool result content in older messages.

        Leaves the most recent _PRUNE_KEEP_RECENT messages untouched so the
        agent keeps full context of recent exchanges. Older tool results are
        trimmed to _PRUNE_RESULT_MAX chars — enough to see what happened without
        bloating the context.
        """
        cutoff = max(0, len(messages) - _PRUNE_KEEP_RECENT)
        for msg in messages[:cutoff]:
            role = msg.get("role")
            if role == "user":
                content = msg.get("content")
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_result":
                            res = block.get("content", "")
                            if isinstance(res, str) and len(res) > _PRUNE_RESULT_MAX:
                                block["content"] = res[:_PRUNE_RESULT_MAX] + " [truncated]"
            elif role == "tool":
                content = msg.get("content", "")
                if isinstance(content, str) and len(content) > _PRUNE_RESULT_MAX:
                    msg["content"] = content[:_PRUNE_RESULT_MAX] + " [truncated]"

    def _extract_readable(self, messages: list[dict]) -> str:
        """Extract human-readable text from messages for the compaction prompt.

        Avoids dumping raw JSON (which includes huge binary-like Pydantic objects)
        and instead produces a concise, readable transcript.
        """
        parts = []
        for m in messages:
            role = m.get("role", "?")
            content = m.get("content", "")
            if isinstance(content, list):
                texts = []
                for block in content:
                    if isinstance(block, dict):
                        btype = block.get("type")
                        if btype == "text":
                            texts.append(block.get("text", "")[:1000])
                        elif btype == "tool_use":
                            inp = json.dumps(block.get("input", {}))[:200]
                            texts.append(f"[Tool: {block.get('name', '?')}({inp})]")
                        elif btype == "tool_result":
                            res = str(block.get("content", ""))[:300]
                            texts.append(f"[Result: {res}]")
                    elif hasattr(block, "type"):

                        if block.type == "text":
                            texts.append(block.text[:1000])
                        elif block.type == "tool_use":
                            texts.append(f"[Tool: {block.name}({json.dumps(block.input)[:200]})]")
                content_str = " ".join(texts)
            elif isinstance(content, str):
                content_str = content[:2000]
            else:
                content_str = ""
            if m.get("tool_calls"):
                tcs = [
                    f"{tc.get('function', {}).get('name', '?')}({tc.get('function', {}).get('arguments', '')[:200]})"
                    for tc in m["tool_calls"]
                ]
                content_str = f"[Tool calls: {', '.join(tcs)}]"
            parts.append(f"[{role}]: {content_str}")
        return "\n\n".join(parts)

    async def _compact(self, messages: list[dict]) -> None:
        """Summarize older history; keep the most recent messages verbatim."""
        if not messages:
            return
        await self.on_event({"type": "compacting"})
        keep = messages[-_COMPACT_KEEP_RECENT:] if len(messages) > _COMPACT_KEEP_RECENT else []
        to_summarize = messages[:-_COMPACT_KEEP_RECENT] if len(messages) > _COMPACT_KEEP_RECENT else messages[:]
        summary_prompt = (
            "Summarize the conversation history below into a concise technical summary. "
            "Include: decisions made, files written or modified (with paths), packages installed, "
            "errors encountered and how they were fixed, and the current state of the project. "
            "Be specific about file names and code decisions. Maximum 500 words.\n\n"
            "CONVERSATION HISTORY:\n"
            + self._extract_readable(to_summarize)
        )
        try:
            summary = await self._internal_llm_call(summary_prompt)
        except Exception:
            summary = "(Conversation summary unavailable — continuing with truncated history.)"
        messages.clear()
        messages.append({"role": "user", "content": f"[Conversation Summary]\n{summary}"})
        messages.append({"role": "assistant", "content": "Understood. Continuing based on the summary above."})
        messages.extend(keep)
        self._last_input_tokens = 0

    async def _ask_user(self, question: str) -> str:
        """Send a clarification question to the user and suspend until they reply."""
        clarification_id = str(uuid4())
        await self.on_event({
            "type": "clarification_request",
            "clarification_id": clarification_id,
            "question": question,
        })
        try:
            answer = await self.request_clarification(clarification_id, question)
            return answer or "(no answer provided)"
        except asyncio.TimeoutError:
            return "(clarification timed out — proceeding with best assumption)"

    async def _update_file_summary(self, path: str, content: str) -> None:
        """Generate a one-line summary for a file and persist it (background task)."""
        try:
            summary_prompt = (
                f"In one sentence (under 15 words), describe what this file does:\n\n"
                f"Path: {path}\n\n{content[:3000]}"
            )
            summary = await self._internal_llm_call(summary_prompt)
            summary = summary.strip().rstrip(".").rstrip("\"'")[:150]
            db = get_database()
            await ProjectFileSummaryCollection.upsert(db, self.project_id, path, summary)
        except Exception:
            logger.debug("File summary failed for %s", path)

    async def _list_files_brief(self) -> str:
        """Return all project files with their one-line summaries."""
        try:
            db = get_database()
            summaries = await ProjectFileSummaryCollection.find_by_project(db, self.project_id)
            if summaries:
                lines = [
                    f"{s['path']}: {s.get('summary', '(no summary)')}"
                    for s in sorted(summaries, key=lambda x: x["path"])
                ]
                return "\n".join(lines)
        except Exception:
            pass

        return await self._glob("**/*")

    async def _internal_llm_call(self, prompt: str) -> str:
        """Non-streaming LLM call for internal use (compaction). No token events emitted."""
        if self.model_provider == "anthropic":
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=self.api_key or settings.ANTHROPIC_API_KEY)
            msg = await client.messages.create(
                model=self.model_id,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )
            return msg.content[0].text if msg.content else ""
        else:
            import openai
            base_url: str | None = None
            api_key = self.api_key or settings.OPENAI_API_KEY
            if self.model_provider in ("ollama", "lmstudio"):
                base_url, api_key = self._resolve_local_client(self.model_provider)
            client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
            resp = await client.chat.completions.create(
                model=self.model_id,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2048,
            )
            return resp.choices[0].message.content or ""
