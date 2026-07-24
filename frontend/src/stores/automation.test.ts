import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { crmStore } from "./crm";
import { automationStore } from "./automation";
import type { AutomationWorkflow } from "../types";

function response(data: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers(),
    json: vi.fn().mockResolvedValue(data),
    text: vi.fn().mockResolvedValue(typeof data === "string" ? data : JSON.stringify(data))
  };
}

const workflow: AutomationWorkflow = {
  id: "workflow-1",
  name: "Discount approval",
  description: null,
  trigger_type: "deal.updated",
  conditions: [{ field: "discount_percent", operator: "gte", value: 20 }],
  condition_logic: "all",
  actions: [{ type: "request_approval", config: { title: "Approve discount", assignee: "owner_manager" } }],
  priority: 100,
  is_active: true,
  version: 3,
  created_by_id: "user-1",
  updated_by_id: "user-1",
  created_at: "2026-07-23T00:00:00Z",
  updated_at: "2026-07-23T00:00:00Z"
};

beforeEach(() => {
  crmStore.token.value = "token-1";
  crmStore.tenantId.value = "tenant-1";
  crmStore.me.value = {
    user_id: "user-1",
    email: "owner@example.test",
    full_name: "Owner",
    tenant_id: "tenant-1",
    role: "owner",
    permissions: ["crm:read", "crm:write", "automations:manage", "approvals:manage"]
  };
  automationStore.workflows.value = [];
  automationStore.templates.value = [];
  automationStore.runs.value = [];
  automationStore.approvals.value = [];
  automationStore.outbox.value = [];
  automationStore.clearMessages();
});

afterEach(() => vi.unstubAllGlobals());

describe("automation store", () => {
  it("loads all permission-backed automation lists", async () => {
    const fetchMock = vi.fn().mockResolvedValue(response([]));
    vi.stubGlobal("fetch", fetchMock);

    await automationStore.refreshAll();

    expect(fetchMock).toHaveBeenCalledTimes(5);
    expect(fetchMock.mock.calls.map(([url]) => String(url))).toEqual(expect.arrayContaining([
      "/api/automations/workflows",
      "/api/automations/templates",
      "/api/automations/runs",
      "/api/automations/approvals",
      "/api/automations/outbox"
    ]));
  });

  it("loads only approvals for approvals-only role", async () => {
    crmStore.me.value = { ...crmStore.me.value!, role: "viewer", permissions: ["crm:read", "approvals:manage"] };
    const fetchMock = vi.fn().mockResolvedValue(response([]));
    vi.stubGlobal("fetch", fetchMock);

    await automationStore.refreshAll();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith("/api/automations/approvals", expect.any(Object));
  });

  it("creates workflow and refreshes its list", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response(workflow, 201))
      .mockResolvedValueOnce(response([workflow]));
    vi.stubGlobal("fetch", fetchMock);

    await automationStore.createWorkflow({
      name: workflow.name,
      trigger_type: "deal.updated",
      conditions: workflow.conditions,
      condition_logic: "all",
      actions: workflow.actions,
      priority: 100,
      is_active: true
    });

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(JSON.parse(String(fetchMock.mock.calls[0][1].body))).toMatchObject({ name: workflow.name });
    expect(automationStore.workflows.value).toHaveLength(1);
  });

  it("sends workflow version for optimistic locking", async () => {
    const updated = { ...workflow, is_active: false, version: 4 };
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response(updated))
      .mockResolvedValueOnce(response([updated]));
    vi.stubGlobal("fetch", fetchMock);

    await automationStore.updateWorkflow(workflow.id, workflow.version, { is_active: false });

    expect(JSON.parse(String(fetchMock.mock.calls[0][1].body))).toEqual({ version: 3, is_active: false });
  });

  it("decides approval then refreshes approvals and runs", async () => {
    const approval = { id: "approval-1", status: "approved" };
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response(approval))
      .mockResolvedValueOnce(response([approval]))
      .mockResolvedValueOnce(response([]));
    vi.stubGlobal("fetch", fetchMock);

    await automationStore.decideApproval("approval-1", 2, "approved", "OK");

    expect(JSON.parse(String(fetchMock.mock.calls[0][1].body))).toEqual({ version: 2, decision: "approved", comment: "OK" });
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("runs scheduled scan and exposes normalized conflicts", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response({ evaluated: 4, matched_runs: 1 }))
      .mockResolvedValueOnce(response([]))
      .mockResolvedValueOnce(response({ detail: { message: "Version conflict", current_version: 4 } }, 409));
    vi.stubGlobal("fetch", fetchMock);

    const result = await automationStore.runScheduled();
    expect(result).toEqual({ evaluated: 4, matched_runs: 1 });

    await expect(automationStore.updateWorkflow("workflow-1", 3, { is_active: false })).rejects.toThrow();
    expect(automationStore.error.value).toContain("Конфликт версии");
  });
});
