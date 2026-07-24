import { computed, readonly, ref } from "vue";

export type ThemePreference = "light" | "system" | "dark";
export type ResolvedTheme = "light" | "dark";

const storageKey = "cmr_ui_theme";
const validPreferences: ThemePreference[] = ["light", "system", "dark"];

function readPreference(): ThemePreference {
  if (typeof localStorage === "undefined") return "system";
  const stored = localStorage.getItem(storageKey) as ThemePreference | null;
  return stored && validPreferences.includes(stored) ? stored : "system";
}

export function resolveTheme(preference: ThemePreference, systemDark: boolean): ResolvedTheme {
  return preference === "system" ? (systemDark ? "dark" : "light") : preference;
}

const preference = ref<ThemePreference>(readPreference());
const systemDark = ref(
  typeof window !== "undefined" && typeof window.matchMedia === "function"
    ? window.matchMedia("(prefers-color-scheme: dark)").matches
    : false
);
const theme = computed(() => resolveTheme(preference.value, systemDark.value));

function applyTheme() {
  if (typeof document === "undefined") return;
  document.documentElement.dataset.theme = theme.value;
  document.documentElement.style.colorScheme = theme.value;
}

export function setTheme(next: ThemePreference) {
  preference.value = next;
  if (typeof localStorage !== "undefined") localStorage.setItem(storageKey, next);
  applyTheme();
}

export function useTheme() {
  return {
    preference: readonly(preference),
    theme: readonly(theme),
    setTheme
  };
}

if (typeof window !== "undefined" && typeof window.matchMedia === "function") {
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  media.addEventListener?.("change", (event) => {
    systemDark.value = event.matches;
    if (preference.value === "system") applyTheme();
  });
}

applyTheme();
