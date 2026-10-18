import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, createCheckout, getMe, getProperty, searchAddresses } from "./api";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

function json(body: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(body), { status }));
}

afterEach(() => fetchMock.mockReset());

describe("api client", () => {
  it("builds the search URL with query and limit", async () => {
    fetchMock.mockReturnValue(json({ results: [] }));
    await searchAddresses("12 exam");
    const [url] = fetchMock.mock.calls[0]!;
    expect(String(url)).toMatch(/\/search\/addresses\?q=12\+exam&limit=8$/);
  });

  it("sends a bearer token and JSON body", async () => {
    fetchMock.mockReturnValue(json({ url: "https://pay.example.com" }));
    await createCheckout("pro_annual", "tok");
    const [, init] = fetchMock.mock.calls[0]!;
    expect(init.method).toBe("POST");
    expect(init.headers.Authorization).toBe("Bearer tok");
    expect(init.body).toBe(JSON.stringify({ plan: "pro_annual" }));
  });

  it("omits Authorization for anonymous property requests", async () => {
    fetchMock.mockReturnValue(json({}));
    await getProperty("900-100001");
    const [, init] = fetchMock.mock.calls[0]!;
    expect(init.headers.Authorization).toBeUndefined();
  });

  it("maps error responses to ApiError with the detail message", async () => {
    fetchMock.mockReturnValue(json({ detail: "Property not found" }, 404));
    await expect(getProperty("x")).rejects.toMatchObject({ status: 404, message: "Property not found" });
    fetchMock.mockReturnValue(json({ detail: "Not authenticated" }, 401));
    await expect(getMe("bad")).rejects.toBeInstanceOf(ApiError);
  });

  it("wraps network failures", async () => {
    fetchMock.mockRejectedValue(new TypeError("fetch failed"));
    await expect(getProperty("x")).rejects.toMatchObject({ status: 0 });
  });
});

describe("api client timeouts", () => {
  it("passes an abort signal so a hung API cannot hang the page", async () => {
    fetchMock.mockReturnValue(json({ results: [] }));
    await searchAddresses("12 exam");
    const [, init] = fetchMock.mock.calls[0]!;
    expect(init.signal).toBeInstanceOf(AbortSignal);
  });

  it("still rethrows caller aborts as AbortError", async () => {
    const ctrl = new AbortController();
    fetchMock.mockImplementation((_url: string, init: RequestInit) => {
      return new Promise((_resolve, reject) => {
        init.signal!.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError")));
      });
    });
    const pending = searchAddresses("12 exam", { signal: ctrl.signal });
    ctrl.abort();
    await expect(pending).rejects.toMatchObject({ name: "AbortError" });
  });
});
