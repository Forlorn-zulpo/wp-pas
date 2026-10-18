const API_BASE = "/api/v1";

interface Tokens {
  access_token: string;
  refresh_token: string;
}

const TOKENS_KEY = "auth_tokens";

export function getTokens(): Tokens | null {
  const raw = localStorage.getItem(TOKENS_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as Tokens;
  } catch {
    return null;
  }
}

export function setTokens(tokens: Tokens | null) {
  if (tokens) {
    localStorage.setItem(TOKENS_KEY, JSON.stringify(tokens));
  } else {
    localStorage.removeItem(TOKENS_KEY);
  }
}

export class ApiError extends Error {
  status: number;
  details?: unknown;

  constructor(status: number, message: string, details?: unknown) {
    super(message);
    this.status = status;
    this.details = details;
  }
}

let refreshPromise: Promise<boolean> | null = null;

async function refreshAccessToken(): Promise<boolean> {
  const tokens = getTokens();
  if (!tokens) return false;

  const resp = await fetch(`${API_BASE}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: tokens.refresh_token }),
  });
  if (!resp.ok) {
    setTokens(null);
    return false;
  }
  const newTokens = (await resp.json()) as Tokens;
  setTokens(newTokens);
  return true;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  skipAuth?: boolean;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, skipAuth = false } = options;

  const doFetch = async (): Promise<Response> => {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (!skipAuth) {
      const tokens = getTokens();
      if (tokens) headers["Authorization"] = `Bearer ${tokens.access_token}`;
    }
    return fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  };

  let resp = await doFetch();

  // Transparent single-flight refresh on 401 (except for auth endpoints themselves).
  if (resp.status === 401 && !skipAuth) {
    if (!refreshPromise) {
      refreshPromise = refreshAccessToken().finally(() => {
        refreshPromise = null;
      });
    }
    const refreshed = await refreshPromise;
    if (refreshed) {
      resp = await doFetch();
    }
  }

  if (!resp.ok) {
    let message = `请求失败 (${resp.status})`;
    let details: unknown;
    try {
      const payload = await resp.json();
      message = payload?.error?.message ?? message;
      details = payload?.error?.details;
    } catch {
      // response had no JSON body
    }
    throw new ApiError(resp.status, message, details);
  }

  if (resp.status === 204) return undefined as T;
  return (await resp.json()) as T;
}
