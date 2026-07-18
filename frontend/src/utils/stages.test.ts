import { describe, expect, it } from "vitest";

import { formatStageName, isTerminalStage } from "./stages";

describe("stage helpers", () => {
  it("normalizes standard English stages", () => {
    expect(formatStageName("proposal")).toBe("КП");
    expect(formatStageName(" Negotiation ")).toBe("Переговоры");
  });

  it("preserves customer-defined stage names", () => {
    expect(formatStageName("Юридическая проверка")).toBe("Юридическая проверка");
  });

  it("handles an empty stage", () => {
    expect(formatStageName(null)).toBe("Без этапа");
  });

  it("recognizes terminal stages", () => {
    expect(isTerminalStage("closed won")).toBe(true);
    expect(isTerminalStage("Закрыты")).toBe(true);
    expect(isTerminalStage("proposal")).toBe(false);
  });
});
