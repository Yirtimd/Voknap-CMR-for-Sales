const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export async function api<T>(
  path: string,
  options: RequestInit = {},
  token?: string,
  tenantId?: string
): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(tenantId ? { "X-Tenant-Id": tenantId } : {}),
      ...options.headers
    }
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `API error ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function post(body: unknown, method = "POST"): RequestInit {
  return { method, body: JSON.stringify(body) };
}

export function emptyToNull<T extends Record<string, unknown>>(source: T): T {
  return Object.fromEntries(
    Object.entries(source).map(([key, value]) => [key, value === "" ? null : value])
  ) as T;
}

