"use client";

import { useEffect } from "react";

/**
 * Sets `data-hydrated="true"` on `<body>` once the client has hydrated, so
 * tests never click a server-only render. See docs/TESTABILITY.md.
 */
export function HydrationMarker() {
  useEffect(() => {
    document.body.setAttribute("data-hydrated", "true");
  }, []);

  return null;
}
