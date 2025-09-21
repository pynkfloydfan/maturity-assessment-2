const DEFAULT_HEADERS: HeadersInit = {
  "Content-Type": "application/json",
  Accept: "application/json",
};

function buildUrl(path: string, params?: Record<string, string | number | boolean | undefined | null>): string {
  const url = new URL(path, window.location.origin);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value === undefined || value === null) return;
      url.searchParams.append(key, String(value));
    });
  }
  return url.pathname + url.search;
}

function safeParseJson<T>(text: string): T | undefined {
  if (!text) return undefined;
  try {
    return JSON.parse(text) as T;
  } catch (error) {
    console.warn("Failed to parse JSON response", error);
    return undefined;
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  const text = await response.text();
  const body = safeParseJson<T>(text);

  if (!response.ok) {
    let message = response.statusText || "Request failed";
    if (body && typeof body === "object") {
      const record = body as Record<string, unknown>;
      if (typeof record.detail === "string") {
        message = record.detail;
      } else if (typeof record.message === "string") {
        message = record.message;
      }
    }
    throw new Error(message);
  }

  if (typeof body !== "undefined") {
    return body;
  }

  return {} as T;
}

export async function apiGet<T>(path: string, params?: Record<string, string | number | boolean | undefined | null>): Promise<T> {
  const url = buildUrl(path, params);
  const response = await fetch(url, {
    method: "GET",
    headers: DEFAULT_HEADERS,
    credentials: "same-origin",
  });
  return handleResponse<T>(response);
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(path, {
    method: "POST",
    headers: DEFAULT_HEADERS,
    body: body ? JSON.stringify(body) : undefined,
    credentials: "same-origin",
  });
  return handleResponse<T>(response);
}

export async function apiPut<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(path, {
    method: "PUT",
    headers: DEFAULT_HEADERS,
    body: body ? JSON.stringify(body) : undefined,
    credentials: "same-origin",
  });
  return handleResponse<T>(response);
}

export async function apiDelete<T>(path: string): Promise<T> {
  const response = await fetch(path, {
    method: "DELETE",
    headers: DEFAULT_HEADERS,
    credentials: "same-origin",
  });
  return handleResponse<T>(response);
}
