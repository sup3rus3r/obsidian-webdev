

export type Framework = "blank" | "react" | "nextjs" | "fastapi" | "fullstack";
export type ProjectStatus = "idle" | "building" | "preparing" | "running" | "stopped" | "error";
export type BuildStatus = "none" | "running" | "passed" | "failed";
export type ModelProvider = "anthropic" | "openai" | "ollama" | "lmstudio" | "obsidian-ai";

export interface Project {
  id: string;
  owner_id: string;
  name: string;
  description: string;
  framework: Framework;
  model_provider: ModelProvider;
  model_id: string;
  status: ProjectStatus;
  build_status: BuildStatus;
  container_id: string | null;
  host_port: number | null;
  host_ports: Record<string, number> | null;
  preview_url: string | null;
  template_ready?: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface ProjectListResponse {
  projects: Project[];
}

export interface ProjectCreate {
  name: string;
  description?: string;
  framework?: Framework;
  model_provider?: ModelProvider;
  model_id?: string;
}

export interface ProjectUpdate {
  name?: string;
  description?: string;
  model_provider?: ModelProvider;
  model_id?: string;
}

export interface ProjectImportGitHub {
  name: string;
  description?: string;
  model_provider?: ModelProvider;
  model_id?: string;
  github_url: string;
}


export type ProviderType = "anthropic" | "openai" | "ollama" | "lmstudio" | "obsidian-ai";

export interface VaultKey {
  id: string;
  provider: ProviderType;
  label: string;
  created_at: string;
  updated_at: string | null;
}

export interface VaultKeyCreate {
  provider: ProviderType;
  label: string;
  value: string;
}

export interface VaultKeyListResponse {
  secrets: VaultKey[];
}

export interface VaultValidateResponse {
  provider: string;
  valid: boolean;
  message: string;
}


export type AgentSessionStatus =
  | "idle"
  | "running"
  | "paused"
  | "completed"
  | "error"
  | "cancelled";

export interface AgentSession {
  session_id: string;
  project_id: string;
  user_id: string;
  status: AgentSessionStatus;
  model_provider: string;
  model_id: string;
  created_at: string | null;
}

export interface AgentSessionCreate {
  project_id: string;
  model_provider?: string;
  model_id?: string;
}

export interface AgentStartRequest {
  user_prompt: string;
  model_provider?: string;
  model_id?: string;
}


export interface ConnectedEvent {
  type: "connected";
  status: "idle" | "running";
}

export interface TokenEvent {
  type: "token";
  content: string;
}

export interface ToolCallEvent {
  type: "tool_call";
  tool: string;
  params: Record<string, unknown>;
}

export interface ToolResultEvent {
  type: "tool_result";
  tool: string;
  result: string;
  denied?: boolean;
}

export interface ToolApprovalRequestEvent {
  type: "tool_approval_request";
  approval_id: string;
  tool: string;
  params: Record<string, unknown>;
}

export interface ClarificationRequestEvent {
  type: "clarification_request";
  clarification_id: string;
  question: string;
}

export interface CompactingEvent {
  type: "compacting";
}

export interface DoneEvent {
  type: "done";
  content: string;
}

export interface StoppedEvent {
  type: "stopped";
}

export interface FileChangedEvent {
  type: "file_changed";
  path: string;
}

export interface ErrorEvent {
  type: "error";
  message: string;
}

export interface HistoryMessage {
  role: string;
  content: string;
  meta?: Record<string, unknown>;
}

export interface HistoryEvent {
  type: "history";
  messages: HistoryMessage[];
}

export type ServerEvent =
  | ConnectedEvent
  | TokenEvent
  | ToolCallEvent
  | ToolResultEvent
  | ToolApprovalRequestEvent
  | ClarificationRequestEvent
  | CompactingEvent
  | DoneEvent
  | StoppedEvent
  | FileChangedEvent
  | ErrorEvent
  | HistoryEvent;


export interface ChatClientMessage {
  type: "chat";
  content: string;
  model_provider?: string;
  model_id?: string;
}

export interface StopMessage {
  type: "stop";
}

export interface ToolApprovalResponseMessage {
  type: "tool_approval_response";
  approval_id: string;
  approved: boolean;
}

export interface SetPermissionModeMessage {
  type: "set_permission_mode";
  mode: "ask" | "auto";
}

export interface ClearHistoryMessage {
  type: "clear_history";
}

export interface ClarificationResponseMessage {
  type: "clarification_response";
  clarification_id: string;
  answer: string;
}

export type ClientEvent =
  | ChatClientMessage
  | StopMessage
  | ToolApprovalResponseMessage
  | ClarificationResponseMessage
  | SetPermissionModeMessage
  | ClearHistoryMessage;


export interface UserPreferences {
  permission_mode:   "ask" | "auto";
  compact_threshold: number;
  max_bash_lines:    number;
  max_file_lines:    number;
  max_web_chars:     number;
}

export interface FileNode {
  name: string;
  path: string;
  type: "file" | "directory";
  children?: FileNode[];
}


export interface ApiError {
  detail: string;
  status: number;
}
