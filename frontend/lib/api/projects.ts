import { apiFetch, apiUrl } from "./client";
import type {
  Project,
  ProjectCreate,
  ProjectListResponse,
  ProjectUpdate,
} from "@/types/api";

export async function listProjects(token: string): Promise<Project[]> {
  const res = await apiFetch<ProjectListResponse>("/projects", {
    method: "GET",
    token,
  });
  return res.projects;
}

export async function getProject(id: string, token: string): Promise<Project> {
  return apiFetch<Project>(`/projects/${id}`, { method: "GET", token });
}

export async function createProject(
  data: ProjectCreate,
  token: string,
): Promise<Project> {
  return apiFetch<Project>("/projects", { method: "POST", body: data, token });
}

export async function updateProject(
  id: string,
  data: ProjectUpdate,
  token: string,
): Promise<Project> {
  return apiFetch<Project>(`/projects/${id}`, {
    method: "PUT",
    body: data,
    token,
  });
}

export async function deleteProject(
  id: string,
  token: string,
): Promise<void> {
  return apiFetch<void>(`/projects/${id}`, { method: "DELETE", token });
}

export async function runProject(id: string, token: string): Promise<Project> {
  return apiFetch<Project>(`/projects/${id}/run`, { method: "POST", token });
}

export async function stopProject(id: string, token: string): Promise<Project> {
  return apiFetch<Project>(`/projects/${id}/stop`, { method: "POST", token });
}

export interface ParsedAttachment {
  type: "text" | "image";
  content: string;
  filename: string;
}

export async function parseAttachment(
  projectId: string,
  file: File,
  token: string,
): Promise<ParsedAttachment> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(apiUrl(`/projects/${projectId}/parse-attachment`), {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json())?.detail ?? detail; } catch {  }
    throw new Error(detail);
  }
  return res.json() as Promise<ParsedAttachment>;
}

export async function probePreview(id: string, token: string): Promise<string | null> {
  const res = await apiFetch<{ preview_url: string | null }>(`/projects/${id}/probe-preview`, {
    method: "GET",
    token,
  });
  return res.preview_url;
}

export async function exportProject(id: string, token: string): Promise<void> {
  const res = await fetch(apiUrl(`/projects/${id}/export`), {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Export failed");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `project-${id}.zip`;
  a.click();
  URL.revokeObjectURL(url);
}
