import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { HydrationMarker } from "./HydrationMarker";

describe("HydrationMarker", () => {
  it("sets data-hydrated=true on <body> once hydrated", () => {
    expect(document.body).not.toHaveAttribute("data-hydrated");

    render(<HydrationMarker />);

    expect(document.body).toHaveAttribute("data-hydrated", "true");
  });
});
