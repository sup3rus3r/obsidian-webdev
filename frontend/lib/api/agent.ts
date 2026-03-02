import { apiFetch } from "./client";
import type {
  AgentSession,
  AgentSessionCreate,
  AgentStartRequest,
} from "@/types/api";

export async function createAgentSession(
  data: AgentSessionCreate,
  token: string,
): Promise<AgentSession> {
  return apiFetch<AgentSession>("/agent/sessions", {
    method: "POST",
    body: data,
    token,
  });
}

export async function getAgentSession(
  sessionId: string,
  token: string,
): Promise<AgentSession> {
  return apiFetch<AgentSession>(`/agent/sessions/${sessionId}`, {
    method: "GET",
    token,
  });
}

export async function listAgentSessions(
  projectId: string,
  token: string,
): Promise<AgentSession[]> {
  return apiFetch<AgentSession[]>(
    `/agent/sessions?project_id=${encodeURIComponent(projectId)}`,
    { method: "GET", token },
  );
}

export async function startAgentSession(
  sessionId: string,
  data: AgentStartRequest,
  token: string,
): Promise<{ status: string; message: string }> {
  return apiFetch(`/agent/sessions/${sessionId}/start`, {
    method: "POST",
    body: data,
    token,
  });
}

export async function stopAgentSession(
  sessionId: string,
  token: string,
): Promise<void> {
  return apiFetch<void>(`/agent/sessions/${sessionId}/stop`, {
    method: "POST",
    token,
  });
}

export async function resumeAgentSession(
  sessionId: string,
  answer: string,
  token: string,
): Promise<{ status: string; message: string }> {
  return apiFetch(`/agent/sessions/${sessionId}/resume`, {
    method: "POST",
    body: { answer },
    token,
  });
}
