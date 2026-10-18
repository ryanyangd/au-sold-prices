/** The only module that talks to the network. */
import { API_BASE_URL, SEARCH } from "./config";
import type {
  BillingPlan,
  Me,
  PropertyResponse,
  SearchResponse,
  UrlResponse,
  AddressResult,
} from "./types";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** Fail instead of hanging when the API or its database is unavailable. */
const REQUEST_TIMEOUT_MS = 15_000;

interface RequestOptions {
  method?: "GET" | "POST";
  token?: string | null;
  body?: unknown;
  signal?: AbortSignal;
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (opts.token) headers.Authorization = `Bearer ${opts.token}`;
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";

  const timeout = AbortSignal.timeout(REQUEST_TIMEOUT_MS);
  const signal = opts.signal ? AbortSignal.any([opts.signal, timeout]) : timeout;

  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      method: opts.method ?? "GET",
      headers,
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
      signal,
      cache: "no-store",
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    throw new ApiError(0, "Network error. Please check your connection and try again.");
  }

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const data = (await res.json()) as { detail?: unknown };
      if (typeof data.detail === "string") detail = data.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

export async function searchAddresses(
  q: string,
  opts: { signal?: AbortSignal; limit?: number } = {},
): Promise<AddressResult[]> {
  const params = new URLSearchParams({ q, limit: String(opts.limit ?? SEARCH.limit) });
  const data = await request<SearchResponse>(`/search/addresses?${params}`, { signal: opts.signal });
  return data.results;
}

export function getProperty(
  id: string,
  opts: { token?: string | null; signal?: AbortSignal } = {},
): Promise<PropertyResponse> {
  return request<PropertyResponse>(`/properties/${encodeURIComponent(id)}`, opts);
}

export function getMe(token: string, signal?: AbortSignal): Promise<Me> {
  return request<Me>("/me", { token, signal });
}

export function createCheckout(plan: BillingPlan, token: string): Promise<UrlResponse> {
  return request<UrlResponse>("/billing/checkout", { method: "POST", token, body: { plan } });
}

export function createPortal(token: string): Promise<UrlResponse> {
  return request<UrlResponse>("/billing/portal", { method: "POST", token });
}

export function getHealth(): Promise<{ status: string }> {
  return request<{ status: string }>("/health");
}
