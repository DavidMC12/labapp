import { useEffect } from "react";

/**
 * The document title of a screen, following docs/SPEC.md section 8's
 * naming idea and the testability contract: `{page} · LabApp`, so a test
 * (or a person with several tabs) knows which page is on top without
 * looking at the content. The root layout already answers `LabApp` for
 * the server render; this hook takes over on the client.
 *
 * An empty or undefined title answers the plain `"LabApp"`. Nothing is
 * restored on unmount: the next page sets its own title.
 *
 * The title is re-asserted whenever something else writes it: a soft
 * navigation (a sort click is one, a search-parameter change of the same
 * screen) makes App Router sync the document title with the route
 * metadata, and a client page has no exported metadata, so it would be
 * left at the plain "LabApp". The browser audit asserts the exact title
 * of every state, including the sorted ones.
 *
 * There is exactly one observer for the whole document, never one per
 * hook call: the detail pages mount two calls of this hook at once, and
 * one observer per call would push two titles against each other for
 * ever. The module state below carries the title the mounted hooks want
 * (the last one whose effect ran owns it) and the count of mounted hooks:
 * the observer is created at the first mount and disconnected only when
 * the last hook unmounts. It restores only a foreign write — when the
 * document title differs from the current one — so two hooks with
 * different titles settle as soon as both effects ran.
 */
let desiredTitle = "LabApp";
let mountedHooks = 0;
let titleObserver: MutationObserver | null = null;

/**
 * Puts the document back on the title the mounted hooks want. It runs
 * from the one shared observer below; the check is the whole work, so
 * the cacophony of head mutations a navigation carries costs nothing.
 */
function assertDesiredTitle(): void {
  if (document.title !== desiredTitle) {
    document.title = desiredTitle;
  }
}

/** Creates the one observer at the first mount. */
function ensureTitleObserver(): void {
  if (titleObserver !== null || mountedHooks === 0) {
    return;
  }
  // The target is the head, never the title element: a navigation may
  // replace the title element entirely (a childList mutation of the
  // head), and an observer pinned to the replaced node would miss every
  // write to the new one.
  titleObserver = new MutationObserver(assertDesiredTitle);
  titleObserver.observe(document.head, {
    childList: true,
    subtree: true,
    characterData: true,
  });
}

/** Disconnects the shared observer only when no hook of this module is mounted. */
function maybeReleaseTitleObserver(): void {
  if (mountedHooks === 0 && titleObserver !== null) {
    titleObserver.disconnect();
    titleObserver = null;
  }
}

export function useDocumentTitle(title: string | undefined): void {
  const page = typeof title === "string" && title.trim() ? title : "";
  const desired = page ? `${page} · LabApp` : "LabApp";

  useEffect(() => {
    desiredTitle = desired;
    document.title = desiredTitle;
    mountedHooks += 1;
    ensureTitleObserver();
    return () => {
      mountedHooks -= 1;
      maybeReleaseTitleObserver();
    };
  }, [desired]);
}
