import { describe, expect, it } from "vitest";

import { statusMeta } from "./statusDictionary";

describe("status dictionary", () => {
  it("maps backend values to localized semantic metadata", () => {
    expect(statusMeta("failed", "outbox")).toEqual({ label: "Ошибка доставки", tone: "danger" });
    expect(statusMeta("sales_manager", "role")).toEqual({ label: "Руководитель продаж", tone: "info" });
    expect(statusMeta("high", "risk")).toEqual({ label: "Высокий риск", tone: "danger" });
  });

  it("normalizes backend spelling and safely humanizes unknown values", () => {
    expect(statusMeta("IN PROGRESS", "task").label).toBe("В работе");
    expect(statusMeta("custom_state").label).toBe("Custom state");
    expect(statusMeta(null).label).toBe("Не указан");
  });
});

