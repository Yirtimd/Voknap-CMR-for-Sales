import type { Pagination } from "./types";

/**
 * In development requests stay on the Vite origin and are forwarded by its
 * `/api` proxy. Production deployments can provide a separate API origin via
 * VITE_API_URL; otherwise the current origin is used.
 */
const API_URL = (import.meta.env.VITE_API_URL ?? (import.meta.env.DEV ? "/api" : "")).replace(/\/$/, "");

export type QueryValue = string | number | boolean | null | undefined;
export type QueryParams = Record<string, QueryValue | QueryValue[]>;

export type ApiResponse<T> = {
  data: T;
  response: Response;
};

export type ApiPage<T> = ApiResponse<T[]> & {
  items: T[];
  pagination: Pagination;
};

export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;
  readonly currentVersion: number | null;

  constructor(status: number, detail: unknown, currentVersion: number | null = null) {
    super(errorMessage(status, detail));
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.currentVersion = currentVersion;
  }
}

export function buildQuery(path: string, query: QueryParams = {}): string {
  const [basePath, existingQuery = ""] = path.split("?", 2);
  const params = new URLSearchParams(existingQuery);

  for (const [key, rawValue] of Object.entries(query)) {
    const values = Array.isArray(rawValue) ? rawValue : [rawValue];
    params.delete(key);
    for (const value of values) {
      if (value !== null && value !== undefined && value !== "") params.append(key, String(value));
    }
  }

  const search = params.toString();
  return search ? `${basePath}?${search}` : basePath;
}

export async function apiResponse<T>(
  path: string,
  options: RequestInit = {},
  token?: string,
  tenantId?: string
): Promise<ApiResponse<T>> {
  const response = await request(path, options, token, tenantId);
  return { data: await readJson<T>(response), response };
}

export async function apiPage<T>(
  path: string,
  options: RequestInit = {},
  token?: string,
  tenantId?: string,
  fallback: Partial<Pagination> = {}
): Promise<ApiPage<T>> {
  const { data, response } = await apiResponse<T[]>(path, options, token, tenantId);
  const items = Array.isArray(data) ? data : [];
  return {
    data: items,
    items,
    response,
    pagination: readPagination(response.headers, items.length, { ...paginationFromPath(path), ...fallback })
  };
}

export async function api<T>(
  path: string,
  options: RequestInit = {},
  token?: string,
  tenantId?: string
): Promise<T> {
  const { data } = await apiResponse<T>(path, options, token, tenantId);
  return data;
}

async function request(
  path: string,
  options: RequestInit = {},
  token?: string,
  tenantId?: string
): Promise<Response> {
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
  const response = await fetch(apiUrl(path), {
    ...options,
    headers: {
      ...(!isFormData ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(tenantId ? { "X-Tenant-Id": tenantId } : {}),
      ...options.headers
    }
  });

  if (!response.ok) {
    throw await toApiError(response);
  }

  return response;
}

export async function apiBlob(path: string, token?: string, tenantId?: string): Promise<Blob> {
  const response = await request(path, {}, token, tenantId);
  return response.blob();
}

export function post(body: unknown, method = "POST"): RequestInit {
  return { method, body: JSON.stringify(body) };
}

export function emptyToNull<T extends Record<string, unknown>>(source: T): T {
  return Object.fromEntries(
    Object.entries(source).map(([key, value]) => [key, value === "" ? null : value])
  ) as T;
}

function apiUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) return path;
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${API_URL}${normalizedPath}`;
}

async function readJson<T>(response: Response): Promise<T> {
  if (response.status === 204 || response.headers.get("content-length") === "0") return undefined as T;
  return response.json() as Promise<T>;
}

async function toApiError(response: Response): Promise<ApiError> {
  const payload = await readErrorPayload(response);
  const detail = isRecord(payload) && "detail" in payload ? payload.detail : payload;
  const currentVersion = currentVersionFrom(detail) ?? currentVersionFrom(payload);
  return new ApiError(response.status, detail, currentVersion);
}

async function readErrorPayload(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

function currentVersionFrom(value: unknown): number | null {
  if (!isRecord(value)) return null;
  const version = value.current_version ?? value.currentVersion;
  return typeof version === "number" && Number.isFinite(version) ? version : null;
}

function errorMessage(status: number, detail: unknown): string {
  if (typeof detail === "string" && detail) return detail;
  if (isRecord(detail) && typeof detail.message === "string") return detail.message;
  return `API error ${status}`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function readPagination(
  headers: Headers,
  itemCount: number,
  fallback: Partial<Pagination>
): Pagination {
  const page = headerNumber(headers, "X-Page", 1) ?? fallback.page ?? 1;
  const pageSize = headerNumber(headers, "X-Page-Size", 1) ?? fallback.pageSize ?? Math.max(itemCount, 1);
  const total = headerNumber(headers, "X-Total-Count") ?? fallback.total ?? itemCount;
  const totalPages =
    headerNumber(headers, "X-Total-Pages", 1) ??
    fallback.totalPages ??
    Math.max(1, Math.ceil(total / pageSize));

  return { page, pageSize, total, totalPages };
}

function headerNumber(headers: Headers, name: string, minimum = 0): number | null {
  const value = headers.get(name);
  if (value === null || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= minimum ? parsed : null;
}

function paginationFromPath(path: string): Partial<Pagination> {
  const queryStart = path.indexOf("?");
  if (queryStart === -1) return {};
  const params = new URLSearchParams(path.slice(queryStart + 1));
  const page = positiveNumber(params.get("page"));
  const pageSize = positiveNumber(params.get("page_size"));
  return { ...(page ? { page } : {}), ...(pageSize ? { pageSize } : {}) };
}

function positiveNumber(value: string | null): number | null {
  if (value === null || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 1 ? parsed : null;
}
