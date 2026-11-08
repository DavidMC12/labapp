// The resource check of the browser audit (task 047): a page that loads its
// own document, script, stylesheet, image or font and the server answers
// 4xx or 5xx is a defect the audit reports, one failure per response.
// Responses of type Fetch and XHR are ignored: the web app itself answers
// 4xx on purpose in the error states the audit walks.

export const TRACKED_TYPES = new Set(["Document", "Stylesheet", "Script", "Image", "Font"]);

/**
 * The failing-resource failures of one state. `state` is the state of
 * states.json: the main document is expected to answer 200 unless the state
 * declares `expectStatus`, for a page that answers 4xx on purpose (the 404
 * page). `responses` are the network responses of the state, in order, as
 * the DevTools Network domain reported them (`{ type, status, url }`).
 * Returns one failure string per tracked response that answered 400 or
 * more. The first Document response of the state is the main document: it
 * is allowed to answer exactly `expectStatus` and nothing else.
 */
export function resourceFailures(state, responses) {
  const expected = state.expectStatus ?? 200;
  const failures = [];
  let documentSeen = false;
  for (const response of responses) {
    if (!TRACKED_TYPES.has(response.type)) continue;
    if ((response.status ?? 0) < 400) continue;
    if (response.type === "Document" && !documentSeen) {
      documentSeen = true;
      if (response.status === expected) continue;
    }
    failures.push(`the ${response.type.toLowerCase()} ${response.url} answered ${response.status}`);
  }
  return failures;
}

/**
 * The site-icon failure of one state. A real browser loads the icon the
 * page declares (`link rel="icon"`, served by the `icon.svg` file
 * convention of Next.js) and asks for `/favicon.ico` when the page
 * declares none; neither request may answer 4xx or 5xx. `icon` is
 * `{ declared: <bool>, href: <resolved url of the fetched request> }` and
 * `status` is the answer of that request (the audit fetches the declared
 * address, or `/favicon.ico` when none is declared: headless Chrome makes
 * no favicon request of its own, and reports the declared one as an
 * untracked `Other` response, both measured).
 */
export function iconFailures(icon, status) {
  if ((status ?? 0) < 400) return [];
  return [icon.declared
    ? `the page declares an icon at ${icon.href} that answers ${status}`
    : `the page declares no icon, so the browser asks for /favicon.ico, which answers ${status}`];
}
