const BASE_URL = import.meta.env.VITE_API_URL || "";

let tokenGetter: () => string | null = () => null;

export function setTokenGetter(fn: () => string | null): void {
  tokenGetter = fn;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const token = tokenGetter();
  const headers: Record<string, string> = {
    "content-type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...((init?.headers as Record<string, string> | undefined) ?? {}),
  };
  const res = await fetch(url, { ...init, headers });
  if (!res.ok) {
    if (res.status === 401) {
      // Let the auth store react (clear token, redirect).
      window.dispatchEvent(new Event("auth:logout"));
    }
    let msg = res.statusText;
    try {
      const body = await res.json();
      if (body?.detail) msg = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      // ignore
    }
    throw new Error(msg || `HTTP ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PATCH", body: body ? JSON.stringify(body) : undefined }),
  del: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};
