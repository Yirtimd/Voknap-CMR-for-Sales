import { readonly, ref } from "vue";

export type UiDensity = "comfortable" | "compact";

const storageKey = "cmr_ui_density";
const savedDensity = localStorage.getItem(storageKey);
const density = ref<UiDensity>(savedDensity === "compact" ? "compact" : "comfortable");

export function setDensity(value: UiDensity) {
  density.value = value;
  localStorage.setItem(storageKey, value);
}

export function useDensity() {
  return {
    density: readonly(density),
    setDensity
  };
}
