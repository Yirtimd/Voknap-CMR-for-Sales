import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { crmStore } from "./crm";
import { lifecycleStore } from "./lifecycle";

afterEach(() => {
  vi.unstubAllGlobals();
});

beforeEach(() => {
  crmStore.token.value = "token";
  crmStore.tenantId.value = "tenant";
  crmStore.me.value = {
    user_id: "owner-1",
    email: "owner@example.test",
    full_name: "Owner",
    tenant_id: "tenant",
    role: "owner",
    permissions: ["crm:read", "crm:write", "sales:manage", "assignments:manage", "members:manage"]
  };
  lifecycleStore.clearSelected();
  lifecycleStore.clearConflict();
  lifecycleStore.records.value = [];
  lifecycleStore.setQuery({ entityType: "contacts", state: "active", search: "", filters: {}, sort: "created_at", order: "desc", page: 1, pageSize: 25 });
});

describe("lifecycle store", () => {
  it("loads the active view with server-side query and pagination", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({
        "X-Total-Count": "42",
        "X-Page": "2",
        "X-Page-Size": "10",
        "X-Total-Pages": "5"
      }),
      json: vi.fn().mockResolvedValue([
        {
          id: "contact-1",
          company_id: "company-1",
          name: "Иван",
          phone: null,
          email: null,
          company_name: null,
          is_archived: false,
          deleted_at: null,
          version: 3
        }
      ])
    });
    vi.stubGlobal("fetch", fetchMock);

    await lifecycleStore.load({
      entityType: "contacts",
      state: "active",
      search: "Иван",
      filters: { owner_id: "owner-1" },
      sort: "name",
      order: "asc",
      page: 2,
      pageSize: 10
    });

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/sales/contacts?"),
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    );
    expect(fetchMock.mock.calls[0][0]).toContain("search=%D0%98%D0%B2%D0%B0%D0%BD");
    expect(fetchMock.mock.calls[0][0]).toContain("owner_id=owner-1");
    expect(lifecycleStore.pagination.value).toEqual({ page: 2, pageSize: 10, total: 42, totalPages: 5 });
    expect(lifecycleStore.records.value[0]).toMatchObject({ id: "contact-1", version: 3 });
  });

  it("keeps id and version in selection for safe bulk requests", () => {
    lifecycleStore.toggleSelected({ id: "lead-1", version: 4 });
    expect(lifecycleStore.selected.value).toEqual([{ id: "lead-1", version: 4 }]);
    lifecycleStore.toggleSelected({ id: "lead-1", version: 4 });
    expect(lifecycleStore.selected.value).toEqual([]);
  });

  it("collects mixed archive pages, filters them, and paginates locally", async () => {
    const records = Array.from({ length: 250 }, (_, index) => ({
      id: `contact-${index + 1}`,
      company_id: "company-1",
      name: `Контакт ${index + 1}`,
      phone: null,
      email: null,
      company_name: null,
      is_archived: true,
      deleted_at: null,
      version: 1
    }));
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, headers: new Headers(), json: vi.fn().mockResolvedValue(records.slice(0, 200)) })
      .mockResolvedValueOnce({ ok: true, status: 200, headers: new Headers(), json: vi.fn().mockResolvedValue(records.slice(200)) });
    vi.stubGlobal("fetch", fetchMock);

    await lifecycleStore.load({ entityType: "contacts", state: "archived", page: 2, pageSize: 100 });

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[0][0]).toContain("include_archived=true");
    expect(fetchMock.mock.calls[0][0]).toContain("page_size=200");
    expect(lifecycleStore.records.value).toHaveLength(100);
    expect(lifecycleStore.pagination.value).toEqual({ page: 2, pageSize: 100, total: 250, totalPages: 3 });
  });

  it("surfaces a 409 conflict without retrying a stale update", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 409,
      headers: new Headers(),
      text: vi.fn().mockResolvedValue('{"detail":{"message":"Version conflict","current_version":9}}')
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(lifecycleStore.update("contacts", { id: "contact-1", version: 3 }, { name: "Новое имя" })).rejects.toMatchObject({ status: 409 });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(lifecycleStore.conflict.value).toMatchObject({ entityType: "contacts", entityId: "contact-1", currentVersion: 9 });
  });
});
