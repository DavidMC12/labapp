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
 */
export function useDocumentTitle(title: string | undefined): void {
  useEffect(() => {
    const page = typeof title === "string" && title.trim() ? title : "";
    document.title = page ? `${page} · LabApp` : "LabApp";
  }, [title]);
}
