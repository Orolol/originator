import { afterEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";

// jsdom has no HTMLDialogElement methods: a minimal stand-in for the native <dialog> the modals use.
// showModal() opens it; close() closes it and fires `close` (what Escape or the close button do in a
// browser), which the components listen to.
if (typeof HTMLDialogElement !== "undefined" && !HTMLDialogElement.prototype.showModal) {
  HTMLDialogElement.prototype.showModal = function showModal(this: HTMLDialogElement) {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function close(this: HTMLDialogElement) {
    if (!this.hasAttribute("open")) return;
    this.removeAttribute("open");
    this.dispatchEvent(new Event("close"));
  };
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  // The dialogs put flags in the URL (lib/urlFlag); start each test from a clean one.
  if (typeof window !== "undefined") window.history.replaceState(null, "", "/");
});
