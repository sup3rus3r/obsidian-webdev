"""Tool definitions and permission tiers for the single ReAct agent.

Permission tiers
  auto   — no user approval needed (read-only / no side effects)
  ask    — ask by default (writes + bash)
  always — always ask regardless of mode (destructive patterns in bash)
"""
from __future__ import annotations

import re


TOOL_TIER: dict[str, str] = {
    "read_file":        "auto",
    "write_file":       "ask",
    "edit_file":        "ask",
    "bash":             "ask",
    "glob":             "auto",
    "grep":             "auto",
    "web_fetch":        "auto",
    "web_search":       "auto",
    "list_files_brief": "auto",
    "ask_user":         "auto",
    "request_done":     "auto",
}

_DESTRUCTIVE_RE = re.compile(
    r"rm\s+-[rRfF]*[rR][fF]?[rRfF]*"
    r"|rm\s+--recursive"
    r"|DROP\s+(TABLE|DATABASE|SCHEMA)\b"
    r"|TRUNCATE\b"
    r"|DELETE\s+FROM\s+\w+\s*;"
    r"|git\s+push\s+(-f|--force)\b"
    r"|mkfs\."
    r"|>\s*/dev/sd",
    re.IGNORECASE,
)


def tool_tier(name: str, params: dict) -> str:
    """Return the effective permission tier for a tool call."""
    tier = TOOL_TIER.get(name, "ask")
    if tier == "ask" and name == "bash" and _DESTRUCTIVE_RE.search(params.get("command", "")):
        return "always"
    return tier


TOOLS_ANTHROPIC: list[dict] = [
    {
        "name": "read_file",
        "description": (
            "Read the contents of a file in /workspace. "
            "Always read a file before modifying it. "
            "Use this instead of bash cat."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file. Absolute /workspace/... or relative to /workspace.",
                },
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": (
            "Create or overwrite a file with the given content. "
            "Use for new files or complete rewrites. "
            "Prefer edit_file for partial changes."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string", "description": "Complete file content to write."},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "edit_file",
        "description": (
            "Surgically replace an exact string in a file. "
            "old_string must appear exactly once in the file. "
            "Use this for targeted edits instead of rewriting the whole file."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old_string": {
                    "type": "string",
                    "description": "Exact text to replace (must be unique in the file).",
                },
                "new_string": {"type": "string", "description": "Replacement text."},
            },
            "required": ["path", "old_string", "new_string"],
        },
    },
    {
        "name": "bash",
        "description": (
            "Execute a shell command in /workspace. Returns stdout+stderr and exit code. "
            "Use for: npm/pip/uv install, builds, tests, git, checking file existence, "
            "running the dev server, or any other shell operation."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to execute."},
            },
            "required": ["command"],
        },
    },
    {
        "name": "glob",
        "description": (
            "Find files matching a glob pattern (e.g. **/*.ts, backend/**/*.py). "
            "Use to explore project structure without opening files."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern, e.g. '**/*.ts' or 'src/**/*.py'.",
                },
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "grep",
        "description": (
            "Search file contents by regex. Use to find function definitions, "
            "imports, usages, or any text pattern across files."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Regex pattern to search for."},
                "path": {
                    "type": "string",
                    "description": "File or directory to search in (default: /workspace).",
                },
                "options": {
                    "type": "string",
                    "description": "Additional grep flags (default: -rn).",
                },
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "web_fetch",
        "description": (
            "Fetch content from a URL. Use for reading documentation, "
            "fetching raw files from GitHub, or checking API references."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to fetch."},
            },
            "required": ["url"],
        },
    },
    {
        "name": "web_search",
        "description": (
            "Search the web. Use when you need to look up how a library works, "
            "find an error solution, or check current documentation."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "ask_user",
        "description": (
            "Ask the user a clarification question and suspend until they respond. "
            "Use ONLY when you have genuine ambiguity that prevents a reasonable decision — "
            "e.g. 'Should I use PostgreSQL or SQLite?' when not specified. "
            "Do NOT use for things you can decide yourself. Make assumptions first; "
            "ask only when truly stuck. Do not call other tools in the same turn as ask_user."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The question to ask the user. Be specific and concise.",
                },
            },
            "required": ["question"],
        },
    },
    {
        "name": "list_files_brief",
        "description": (
            "List all project files with a one-line AI-generated summary of what each file does. "
            "Use this to understand the codebase structure before deciding which files to open. "
            "Much faster than reading every file individually. Falls back to a plain file list "
            "if summaries are not yet available."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "request_done",
        "description": (
            "Signal that you have completed all tasks and request user approval before stopping. "
            "You MUST call this tool when you believe the work is done — never just stop responding. "
            "Provide a clear summary of everything you built or changed. "
            "The user will review and either approve (you stop) or send feedback (you continue)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "A concise summary of what was built or changed. List key files created/modified and what the app does.",
                },
            },
            "required": ["summary"],
        },
    },
]


def _to_openai(tool: dict) -> dict:
    return {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["input_schema"],
        },
    }


TOOLS_OPENAI: list[dict] = [_to_openai(t) for t in TOOLS_ANTHROPIC]
