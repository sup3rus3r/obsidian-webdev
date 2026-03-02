import { apiFetch } from "./client";
import type { FileNode } from "@/types/api";

export interface ProjectFile {
  id: string;
  project_id: string;
  path: string;
  content: string;
  language: string;
  summary: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface FileListItem {
  id: string;
  project_id: string;
  path: string;
  language: string;
  summary: string | null;
  updated_at: string | null;
}

export async function listFiles(
  projectId: string,
  token: string,
): Promise<FileListItem[]> {
  const res = await apiFetch<{ files: FileListItem[] }>(
    `/projects/${projectId}/files`,
    { method: "GET", token },
  );
  return res.files;
}

export async function getFile(
  projectId: string,
  path: string,
  token: string,
): Promise<ProjectFile> {
  return apiFetch<ProjectFile>(
    `/projects/${projectId}/files/${encodeURIComponent(path)}`,
    { method: "GET", token },
  );
}

export async function writeFile(
  projectId: string,
  path: string,
  content: string,
  token: string,
): Promise<ProjectFile> {
  return apiFetch<ProjectFile>(`/projects/${projectId}/files`, {
    method: "POST",
    body: { path, content },
    token,
  });
}

export async function deleteFile(
  projectId: string,
  path: string,
  token: string,
): Promise<void> {
  return apiFetch<void>(
    `/projects/${projectId}/files/${encodeURIComponent(path)}`,
    { method: "DELETE", token },
  );
}


export function buildFileTree(files: FileListItem[]): FileNode[] {
  const root: FileNode[] = [];
  const dirMap = new Map<string, FileNode>();

  const ensureDir = (parts: string[], upTo: number): FileNode[] => {
    const key = parts.slice(0, upTo).join("/");
    if (dirMap.has(key)) return dirMap.get(key)!.children!;
    const node: FileNode = {
      name: parts[upTo - 1],
      path: key,
      type: "directory",
      children: [],
    };
    dirMap.set(key, node);
    const parentChildren =
      upTo === 1 ? root : ensureDir(parts, upTo - 1);
    parentChildren.push(node);
    return node.children!;
  };

  for (const file of files) {
    const parts = file.path.split("/");
    const parentChildren =
      parts.length === 1 ? root : ensureDir(parts, parts.length - 1);
    parentChildren.push({
      name: parts[parts.length - 1],
      path: file.path,
      type: "file",
    });
  }

  return root;
}
