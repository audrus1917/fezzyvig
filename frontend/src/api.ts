export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = "ApiError";
  }
}

export const unauthorizedEvent = "fezzyvig:unauthorized";

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(path, { ...options, headers });
  if (!response.ok) {
    if (response.status === 401) window.dispatchEvent(new Event(unauthorizedEvent));
    let message = `Ошибка ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      message = body.detail ?? message;
    } catch {
      // Preserve the status when a proxy returns a non-JSON response.
    }
    throw new ApiError(message, response.status);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
