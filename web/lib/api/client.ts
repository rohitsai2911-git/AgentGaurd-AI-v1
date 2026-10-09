/**
 * Transport layer for the AgentGuard AI backend.
 * Every response is real. Nothing here fabricates data.
 */

import { clearAuth, getToken } from "../auth";

export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8077"
).replace(/\/+$/, "");

export const APP_NAME = process.env.NEXT_PUBLIC_APP_NAME ?? "AgentGuard AI";

const REQUEST_TIMEOUT_MS = 25_000;

interface ApiErrorEnvelope {
  error?: { code?: string; message?: string; details?: unknown };
  request_id?: string;
}

/** Backend error envelope: { error: { code, message, details }, request_id } */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: unknown;
  readonly requestId?: string;

  constructor(
    message: string,
    status: number,
    code: string,
    details: unknown = {},
    requestId?: string,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
    this.requestId = requestId;
  }

  /** True when the request never reached the backend. */
  get isOffline(): boolean {
    return this.status === 0;
  }
}

export function buildQuery(params: object): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  const token = getToken();
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      cache: "no-store",
      signal: controller.signal,
      headers: {
        Accept: "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
        ...(init?.headers ?? {}),
      },
    });
  } catch (error) {
    clearTimeout(timer);
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError(
        `The backend did not respond within ${REQUEST_TIMEOUT_MS / 1000}s.`,
        0,
        "TIMEOUT",
        { path },
      );
    }
    throw new ApiError(
      `Cannot reach the AgentGuard API at ${API_BASE_URL}.`,
      0,
      "NETWORK_ERROR",
      { path, api_base_url: API_BASE_URL },
    );
  }
  clearTimeout(timer);

  if (response.status === 204) {
    return undefined as T;
  }

  const raw = await response.text();
  let body: unknown = null;
  if (raw) {
    try {
      body = JSON.parse(raw);
    } catch {
      body = raw;
    }
  }

  if (!response.ok) {
    if (response.status === 401) {
      // Token missing/expired — drop it so the app routes back to login.
      clearAuth();
    }
    const envelope = (body ?? {}) as ApiErrorEnvelope;
    const message =
      envelope.error?.message ??
      (typeof body === "string" && body.trim()) ??
      `Request failed with status ${response.status}.`;
    throw new ApiError(
      String(message),
      response.status,
      envelope.error?.code ?? `HTTP_${response.status}`,
      envelope.error?.details ?? {},
      envelope.request_id,
    );
  }

  return body as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "POST",
      body: body === undefined ? undefined : JSON.stringify(body),
    }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};

/** Streams a JSON export from the backend to the user's disk. */
export async function downloadJson(path: string, filename: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw new ApiError(
      `Export failed with status ${response.status}.`,
      response.status,
      `HTTP_${response.status}`,
    );
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}