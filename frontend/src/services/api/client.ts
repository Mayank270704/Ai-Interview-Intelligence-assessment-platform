export const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

const TOKEN_STORAGE_KEY = "aii.access_token";

let accessToken: string | null = null;

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

/** Store the bearer token used for every subsequent request (and across reloads). */
export function setAccessToken(token: string | null): void {
  accessToken = token;
  if (typeof window === "undefined") {
    return;
  }
  try {
    if (token) {
      window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
    } else {
      window.localStorage.removeItem(TOKEN_STORAGE_KEY);
    }
  } catch {
    // Storage can be unavailable (private mode, blocked cookies); the in-memory
    // token still works for the current page.
  }
}

let unauthorizedHandler: (() => void) | null = null;

/**
 * Register what should happen when the API rejects a stored token mid-session.
 * Without this a session that expired while the tab was open keeps rendering as
 * signed in, and every request fails with an error the user cannot act on.
 */
export function setUnauthorizedHandler(handler: (() => void) | null): void {
  unauthorizedHandler = handler;
}

/** The credential endpoints answer 401 for bad credentials, not an expired session. */
function isCredentialEndpoint(path: string): boolean {
  return path.startsWith("/auth/login") || path.startsWith("/auth/signup");
}

export function getAccessToken(): string | null {
  if (accessToken !== null) {
    return accessToken;
  }
  if (typeof window === "undefined") {
    return null;
  }
  try {
    accessToken = window.localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    accessToken = null;
  }
  return accessToken;
}

function friendlyMessage(status: number, detail: string | undefined): string {
  switch (status) {
    case 401:
      return "Your session has expired. Please sign in again.";
    case 403:
      return "You don't have access to this.";
    case 404:
    case 409:
    case 413:
    case 415:
    case 429:
      return detail ?? "The request could not be completed.";
    case 422:
      return "We couldn't process that file or request. Please check it and try again.";
    case 502:
      return "The AI service didn't respond in time. Please try again in a moment.";
    case 503:
      // A 503 is a server that is not configured or a database that is down --
      // retrying immediately will fail the same way, so don't invite it.
      return detail ?? "This feature is temporarily unavailable. Please try again later.";
    default:
      return "Something went wrong on our end. Please try again in a moment.";
  }
}

async function readErrorDetail(response: Response): Promise<string | undefined> {
  try {
    const body = await response.json();
    return typeof body?.detail === "string" ? body.detail : undefined;
  } catch {
    return undefined;
  }
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  const token = getAccessToken();
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, "Unable to reach the server. Please check your connection and try again.");
  }

  if (!response.ok) {
    const detail = await readErrorDetail(response);
    if (response.status === 401 && !isCredentialEndpoint(path)) {
      setAccessToken(null);
      unauthorizedHandler?.();
    }
    throw new ApiError(response.status, friendlyMessage(response.status, detail));
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
