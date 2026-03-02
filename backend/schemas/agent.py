"""WebSocket + HTTP event schemas for the agent communication layer."""
from datetime import datetime
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel


class AssistantTokenEvent(BaseModel):
    """A single streaming token from the pre-build conversational assistant."""
    type: Literal["assistant_token"] = "assistant_token"
    token: str


class AssistantDoneEvent(BaseModel):
    """The pre-build assistant has finished streaming its response."""
    type: Literal["assistant_done"] = "assistant_done"


class BuildProposalEvent(BaseModel):
    """The assistant is proposing to start building — requires user confirmation."""
    type: Literal["build_proposal"] = "build_proposal"
    prompt: str
    summary: str


class AgentTokenEvent(BaseModel):
    """A single streaming token from the LLM currently running."""
    type: Literal["agent_token"] = "agent_token"
    agent: str
    token: str


class ToolCallEvent(BaseModel):
    """An agent is about to invoke a tool."""
    type: Literal["tool_call"] = "tool_call"
    agent: str
    tool: str
    args: dict[str, Any]
    call_id: str


class ToolResultEvent(BaseModel):
    """Result of a tool call."""
    type: Literal["tool_result"] = "tool_result"
    call_id: str
    success: bool
    output: Any


class FileWriteEvent(BaseModel):
    """A project file was written (emitted directly from write_file tool)."""
    type: Literal["file_write"] = "file_write"
    project_id: str
    path: str


class BuildEvent(BaseModel):
    """Build stage status update."""
    type: Literal["build_event"] = "build_event"
    project_id: str
    stage: str
    status: str
    output: Optional[str] = None


class HumanPauseEvent(BaseModel):
    """Agent is pausing to ask the user a question (human-in-the-loop)."""
    type: Literal["human_pause"] = "human_pause"
    question: str
    context: Optional[str] = None


class AgentStatusEvent(BaseModel):
    """Notifies the client that an agent node changed state."""
    type: Literal["agent_status"] = "agent_status"
    agent: str
    status: str
    message: Optional[str] = None


class AgentDoneEvent(BaseModel):
    """The entire agent graph run finished (pass or fail)."""
    type: Literal["agent_done"] = "agent_done"
    build_status: str
    message: Optional[str] = None


class ErrorEvent(BaseModel):
    """An unexpected error occurred in the agent pipeline or WebSocket layer."""
    type: Literal["error"] = "error"
    message: str
    code: Optional[str] = None


ServerEvent = Union[
    AssistantTokenEvent,
    AssistantDoneEvent,
    BuildProposalEvent,
    AgentTokenEvent,
    ToolCallEvent,
    ToolResultEvent,
    FileWriteEvent,
    BuildEvent,
    HumanPauseEvent,
    AgentStatusEvent,
    AgentDoneEvent,
    ErrorEvent,
]


class ChatMessage(BaseModel):
    """User sends a new prompt to start (or continue) an agent run directly."""
    type: Literal["chat"] = "chat"
    content: str
    model_provider: Optional[str] = None
    model_id: Optional[str] = None


class ConverseMessage(BaseModel):
    """User message for pre-build assistant conversation."""
    type: Literal["converse"] = "converse"
    content: str
    history: list[dict] = []
    model_provider: Optional[str] = None
    model_id: Optional[str] = None


class StartBuildMessage(BaseModel):
    """User confirmed the build proposal — start the build pipeline."""
    type: Literal["start_build"] = "start_build"
    prompt: str
    model_provider: Optional[str] = None
    model_id: Optional[str] = None


class HumanReplyEvent(BaseModel):
    """User answers a human-in-the-loop question to resume the graph."""
    type: Literal["human_reply"] = "human_reply"
    content: str


class SessionControlEvent(BaseModel):
    """Control the running session."""
    type: Literal["session_control"] = "session_control"
    action: Literal["pause", "resume", "cancel"]


ClientEvent = Union[
    ChatMessage,
    ConverseMessage,
    StartBuildMessage,
    HumanReplyEvent,
    SessionControlEvent,
]


class AgentSessionCreate(BaseModel):
    """Body for POST /agent/sessions — creates a new agent session."""
    project_id: str
    model_provider: str = "anthropic"
    model_id: str = "claude-sonnet-4-6"


class AgentSessionResponse(BaseModel):
    """Response from POST /agent/sessions and GET /agent/sessions/{id}."""
    session_id: str
    project_id: str
    user_id: str
    status: str
    model_provider: str
    model_id: str
    created_at: Optional[datetime] = None


class AgentStartRequest(BaseModel):
    """Body for POST /agent/sessions/{id}/start."""
    user_prompt: str
    model_provider: Optional[str] = None
    model_id: Optional[str] = None


class AgentResumeRequest(BaseModel):
    """Body for POST /agent/sessions/{id}/resume — human-in-the-loop answer."""
    answer: str
