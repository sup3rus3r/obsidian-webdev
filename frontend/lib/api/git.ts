import { apiFetch } from "./client";
import type { GitStatus, GitCommit, GitBranches, GitRemote } from "@/types/api";

const base = (projectId: string) => `/git/${projectId}`;

export async function gitStatus(projectId: string, token: string): Promise<GitStatus> {
  return apiFetch<GitStatus>(`${base(projectId)}/status`, { token });
}

export async function gitLog(projectId: string, token: string, limit = 20): Promise<GitCommit[]> {
  return apiFetch<GitCommit[]>(`${base(projectId)}/log?limit=${limit}`, { token });
}

export async function gitBranches(projectId: string, token: string): Promise<GitBranches> {
  return apiFetch<GitBranches>(`${base(projectId)}/branches`, { token });
}

export async function gitPull(projectId: string, token: string): Promise<{ output: string }> {
  return apiFetch(`${base(projectId)}/pull`, { method: "POST", body: {}, token });
}

export async function gitPush(projectId: string, token: string): Promise<{ output: string }> {
  return apiFetch(`${base(projectId)}/push`, { method: "POST", body: {}, token });
}

export async function gitCommit(
  projectId: string,
  message: string,
  token: string,
): Promise<{ output: string }> {
  return apiFetch(`${base(projectId)}/commit`, {
    method: "POST",
    body: { message, stage_all: true },
    token,
  });
}

export async function gitCheckout(
  projectId: string,
  branch: string,
  create: boolean,
  token: string,
): Promise<{ output: string }> {
  return apiFetch(`${base(projectId)}/checkout`, {
    method: "POST",
    body: { branch, create },
    token,
  });
}

export async function gitRemotes(projectId: string, token: string): Promise<GitRemote[]> {
  return apiFetch<GitRemote[]>(`${base(projectId)}/remotes`, { token });
}

export async function gitSetRemote(
  projectId: string,
  url: string,
  token: string,
): Promise<{ output: string; success: boolean }> {
  return apiFetch(`${base(projectId)}/remote`, {
    method: "POST",
    body: { url, name: "origin" },
    token,
  });
}

export async function gitInit(projectId: string, token: string): Promise<{ output: string; success: boolean }> {
  return apiFetch(`${base(projectId)}/init`, { method: "POST", body: {}, token });
}

export async function gitClone(projectId: string, url: string, token: string): Promise<{ output: string; success: boolean }> {
  return apiFetch(`${base(projectId)}/clone`, { method: "POST", body: { url }, token });
}
