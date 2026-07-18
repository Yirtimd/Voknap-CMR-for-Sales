import { afterEach, describe, expect, it, vi } from "vitest";

import { api, emptyToNull, post } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("API client", () => {
  it("adds authentication and tenant headers", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ id: "user-1" })
    });
    vi.stubGlobal("fetch", fetchMock);

    await api("/me", {}, "token-1", "tenant-1");

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/me",
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer token-1",
          "X-Tenant-Id": "tenant-1"
        })
      })
    );
  });

  it("propagates an API error body", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 403,
        text: vi.fn().mockResolvedValue("Tenant access denied")
      })
    );

    await expect(api("/sales/companies")).rejects.toThrow("Tenant access denied");
  });

  it("normalizes form payloads", () => {
    expect(emptyToNull({ name: "Company", website: "" })).toEqual({
      name: "Company",
      website: null
    });
    expect(post({ title: "Deal" }, "PATCH")).toEqual({
      method: "PATCH",
      body: '{"title":"Deal"}'
    });
  });
});
