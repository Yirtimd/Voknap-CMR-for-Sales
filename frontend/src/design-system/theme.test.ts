import { afterEach, describe, expect, it } from "vitest";

import { resolveTheme, setTheme, useTheme } from "./theme";

describe("UI theme", () => {
  afterEach(() => {
    setTheme("system");
    localStorage.removeItem("cmr_ui_theme");
  });

  it("resolves system preference", () => {
    expect(resolveTheme("system", true)).toBe("dark");
    expect(resolveTheme("system", false)).toBe("light");
  });

  it("shares, persists and applies dark theme", () => {
    setTheme("dark");

    expect(useTheme().preference.value).toBe("dark");
    expect(useTheme().theme.value).toBe("dark");
    expect(localStorage.getItem("cmr_ui_theme")).toBe("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");
  });
});
