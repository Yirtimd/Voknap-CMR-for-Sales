import { nextTick, onBeforeUnmount, type Ref, watch } from "vue";

const focusableSelector = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "[tabindex]:not([tabindex='-1'])"
].join(",");

export function useOverlay(open: Ref<boolean>, root: Ref<HTMLElement | null>, close: () => void) {
  let previousFocus: HTMLElement | null = null;
  let previousOverflow = "";

  function onKeydown(event: KeyboardEvent) {
    if (event.key === "Escape") {
      event.preventDefault();
      close();
      return;
    }
    if (event.key !== "Tab" || !root.value) return;
    const focusable = Array.from(root.value.querySelectorAll<HTMLElement>(focusableSelector));
    if (!focusable.length) {
      event.preventDefault();
      root.value.focus();
      return;
    }
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  function deactivate() {
    document.removeEventListener("keydown", onKeydown);
    document.body.style.overflow = previousOverflow;
    previousFocus?.focus();
    previousFocus = null;
  }

  watch(
    open,
    async (isOpen) => {
      if (!isOpen) {
        deactivate();
        return;
      }
      previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
      previousOverflow = document.body.style.overflow;
      document.body.style.overflow = "hidden";
      document.addEventListener("keydown", onKeydown);
      await nextTick();
      root.value?.querySelector<HTMLElement>("[autofocus], button, input, select, textarea, a[href]")?.focus();
    },
    { immediate: true }
  );

  onBeforeUnmount(deactivate);
}

