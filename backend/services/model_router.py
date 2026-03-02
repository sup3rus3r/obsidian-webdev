"""Model Router.

Responsibilities:
  - get_model(provider, model_id, api_key, base_url)  → LangChain BaseChatModel
  - get_model_for_user(provider, model_id, user_id)   → BaseChatModel (vault key lookup)
  - CONTEXT_BUDGETS                                   → token limits per model
  - count_tokens(messages)                            → approximate token count
  - compress_history(messages, keep_recent)           → trim old messages
  - build_agent_context(state, model_id, system_prompt) → context list within budget

Provider strategy:
  anthropic  → ChatAnthropic
  openai     → ChatOpenAI
  ollama     → ChatOllama  (local, base_url from vault or settings)
  lmstudio   → ChatOpenAI  (OpenAI-compatible local API)

Token budgets are conservative — well below advertised context windows.
Local models (ollama/lmstudio) default to 6 000 tokens to stay safe with any
quantised model that ships with a short context window.
"""
from __future__ import annotations

import logging
from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, ToolMessage

logger = logging.getLogger(__name__)


CONTEXT_BUDGETS: dict[str, int] = {
    "claude-opus-4-6":           800_000,
    "claude-sonnet-4-6":         800_000,
    "claude-haiku-4-5-20251001": 200_000,
    "gpt-4.1":                   800_000,
    "gpt-4.1-mini":              800_000,
    "o3":                        200_000,
    "o4-mini":                   200_000,
}

_LOCAL_BUDGET = 6_000
_CLOUD_BUDGET = 100_000


def _get_budget(provider: str, model_id: str) -> int:
    if model_id in CONTEXT_BUDGETS:
        return CONTEXT_BUDGETS[model_id]
    if provider in ("ollama", "lmstudio"):
        return _LOCAL_BUDGET
    return _CLOUD_BUDGET


_CHEAP_MODEL: dict[str, str] = {
    "anthropic": "claude-haiku-4-5-20251001",
    "openai":    "gpt-4.1-mini",
}


def get_cheap_model_id(provider: str) -> Optional[str]:
    """Return the fastest/cheapest model ID for a provider, or None for local providers."""
    return _CHEAP_MODEL.get(provider)


def get_model(
    provider: str,
    model_id: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> BaseChatModel:
    """Instantiate and return the appropriate LangChain chat model.

    This is a synchronous factory — it only creates the model object.
    To inject the user's vault API key, use ``get_model_for_user`` instead.

    Args:
        provider: One of "anthropic", "openai", "ollama", "lmstudio".
        model_id: Provider-specific model identifier.
        api_key:  API key string (optional; omit to use env var or app-level key).
        base_url: Override base URL (used for ollama/lmstudio).
    """
    match provider:
        case "anthropic":
            from langchain_anthropic import ChatAnthropic
            kwargs: dict = {"model": model_id}
            if api_key:
                kwargs["api_key"] = api_key
            return ChatAnthropic(**kwargs)

        case "openai":
            from langchain_openai import ChatOpenAI
            kwargs = {"model": model_id}
            if api_key:
                kwargs["api_key"] = api_key
            return ChatOpenAI(**kwargs)

        case "ollama":
            from langchain_ollama import ChatOllama
            from config import settings
            return ChatOllama(
                model=model_id,
                base_url=base_url or settings.OLLAMA_BASE_URL,
            )

        case "lmstudio":
            from langchain_openai import ChatOpenAI
            from config import settings
            return ChatOpenAI(
                model=model_id,
                base_url=base_url or settings.LMSTUDIO_BASE_URL,
                api_key="lm-studio",
            )

        case _:
            raise ValueError(f"Unknown model provider: {provider!r}")


async def get_model_for_user(
    provider: str,
    model_id: str,
    user_id: str,
) -> BaseChatModel:
    """Return a LangChain model configured with the user's vault API key.

    Falls back to the app-level key from ``settings`` if no vault entry exists.
    For local providers (ollama/lmstudio), the vault stores the base URL.
    """
    api_key: Optional[str] = None
    base_url: Optional[str] = None

    try:
        from services.embedding_service import _get_vault_key
        if provider in ("anthropic", "openai"):
            api_key = await _get_vault_key(user_id, provider)
        elif provider in ("ollama", "lmstudio"):
            base_url = await _get_vault_key(user_id, provider)
    except Exception as exc:
        logger.debug("Vault key lookup failed for %s/%s: %s", user_id, provider, exc)

    if not api_key and provider in ("anthropic", "openai"):
        from config import settings
        if provider == "anthropic":
            api_key = settings.ANTHROPIC_API_KEY or None
        elif provider == "openai":
            api_key = settings.OPENAI_API_KEY or None

    return get_model(provider, model_id, api_key=api_key, base_url=base_url)


def count_tokens(messages: list[BaseMessage]) -> int:
    """Approximate token count for a list of messages.

    Uses tiktoken (cl100k_base) — a close approximation for all models.
    Falls back to character ÷ 4 if tiktoken is unavailable.
    """
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        total = 0
        for msg in messages:
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            total += len(enc.encode(content)) + 4
        return total
    except Exception:
        total = 0
        for msg in messages:
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            total += max(1, len(content) // 4)
        return total


def compress_history(
    messages: list[BaseMessage],
    keep_recent: int = 10,
) -> list[BaseMessage]:
    """Return the most recent ``keep_recent`` messages, dropping older ones.

    This is a lightweight trim — no LLM is called here.  Full LLM-based history
    summarisation (which replaces dropped messages with a summary) is implemented
    as a LangGraph node (``summarize_history`` node).

    Args:
        messages:    Full message list from BuildState.
        keep_recent: Maximum number of messages to retain (from the tail).

    Returns:
        Trimmed list; unchanged if already within the limit.
    """
    if len(messages) <= keep_recent:
        return messages
    return messages[-keep_recent:]


def build_agent_context(
    state: dict,
    model_id: str,
    system_prompt: str,
) -> list[BaseMessage]:
    """Assemble a message list that fits within the model's context budget.

    Assembly order (highest → lowest priority):
      1. System prompt             — always included
      2. Recent conversation history — trimmed to fit remaining budget

    For local models, history is limited to 5 messages to stay within the
    tight 6 K token budget.  Cloud models keep up to 20 recent messages.

    Args:
        state:         LangGraph BuildState dict.
        model_id:      Model ID used to look up the context budget.
        system_prompt: The agent's system prompt string.

    Returns:
        List of BaseMessage objects ready to pass directly to the LLM.
    """
    provider = state.get("model_provider", "openai")
    budget = _get_budget(provider, model_id)

    system_msg = SystemMessage(content=system_prompt)
    system_tokens = count_tokens([system_msg])
    remaining = budget - system_tokens

    all_messages: list[BaseMessage] = state.get("messages", [])

    keep = 5 if provider in ("ollama", "lmstudio") else 20
    trimmed = compress_history(all_messages, keep_recent=keep)

    while trimmed and count_tokens(trimmed) > remaining:
        trimmed = trimmed[1:]
        while trimmed and isinstance(trimmed[0], ToolMessage):
            trimmed = trimmed[1:]

    while trimmed and isinstance(trimmed[0], ToolMessage):
        trimmed = trimmed[1:]

    while (
        trimmed
        and isinstance(trimmed[0], AIMessage)
        and getattr(trimmed[0], "tool_calls", None)
        and (len(trimmed) < 2 or not isinstance(trimmed[1], ToolMessage))
    ):
        trimmed = trimmed[1:]

    return [system_msg] + trimmed
