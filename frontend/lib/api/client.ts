

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:7412";


let _onUnauthorized: (() => void) | null = null;

export function setOnUnauthorized(cb: () => void): void {
  _onUnauthorized = cb;
}

export function clearOnUnauthorized(): void {
  _onUnauthorized = null;
}

export function apiUrl(path: string): string {
  return `${BASE}${path}`;
}


export function wsUrl(path: string): string {
  const base = BASE.replace(/^http/, "ws");
  return `${base}${path}`;
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

interface FetchOptions extends Omit<RequestInit, "body"> {
  token?: string;
  body?: unknown;
}

export async function apiFetch<T>(
  path: string,
  { token, body, headers: extraHeaders, ...rest }: FetchOptions = {},
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(extraHeaders as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(apiUrl(path), {
    ...rest,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    if (res.status === 401) {
      _onUnauthorized?.();
    }
    let detail = res.statusText;
    try {
      const json = await res.json();
      detail = json?.detail ?? detail;
    } catch {
      
    }
    throw new ApiError(res.status, detail);
  }

  
  if (res.status === 204) return undefined as T;

  return res.json() as Promise<T>;
}
