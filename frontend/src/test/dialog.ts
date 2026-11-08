/**
 * Test helper for the native `<dialog>` element: jsdom implements the
 * element (the `open` attribute included) but not `showModal()` and
 * `close()`, so the tests that mount a dialog stub those two on the
 * prototype the same way the browser would behave for the code under
 * test: `showModal()` sets `open`, `close()` removes it.
 *
 * Every test file that mounts a dialog calls this helper once (a
 * `beforeEach` or the top of the file); the stub is inert when the test
 * runner one day implements the real methods.
 */
export function installDialogStub(): void {
  if (typeof HTMLDialogElement === "undefined") {
    return;
  }
  const prototype = HTMLDialogElement.prototype as unknown as Record<
    string,
    unknown
  >;
  if (typeof prototype.showModal !== "function") {
    prototype.showModal = function showModal(this: HTMLDialogElement) {
      this.setAttribute("open", "");
    };
  }
  if (typeof prototype.close !== "function") {
    prototype.close = function close(this: HTMLDialogElement) {
      this.removeAttribute("open");
    };
  }
}
