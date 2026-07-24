import { afterEach, describe, expect, it } from "vitest";

import { setDensity, useDensity } from "./density";

describe("UI density", () => {
  afterEach(() => {
    setDensity("comfortable");
    localStorage.removeItem("cmr_ui_density");
  });

  it("shares and persists compact density", () => {
    setDensity("compact");

    expect(useDensity().density.value).toBe("compact");
    expect(localStorage.getItem("cmr_ui_density")).toBe("compact");
  });

  it("restores comfortable density", () => {
    setDensity("comfortable");

    expect(useDensity().density.value).toBe("comfortable");
    expect(localStorage.getItem("cmr_ui_density")).toBe("comfortable");
  });
});
