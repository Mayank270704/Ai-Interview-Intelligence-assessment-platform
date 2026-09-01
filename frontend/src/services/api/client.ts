export const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function friendlyMessage(status: number, detail: string | undefined): string {
  switch (status) {
    case 404:
    case 409:
    case 413:
    case 415:
      return detail ?? "The request could not be completed.";
    case 422:
      return "We couldn't process that file or request. Please check it and try again.";
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
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl}${path}`, init);
  } catch {
    throw new ApiError(0, "Unable to reach the server. Please check your connection and try again.");
  }

  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new ApiError(response.status, friendlyMessage(response.status, detail));
  }

  return (await response.json()) as T;
}
