import { renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useDocumentTitle } from "./useDocumentTitle";

/**
 * Waits, with a bounded number of microtask/timeout rounds, until the
 * document carries the expected title. A loop here fails after 20
 * rounds instead of hanging: a bouncing title never settles and the
 * assertion says so in seconds (a per-call observer would not).
 */
async function waitForRestored(expected: string): Promise<void> {
  for (let round = 0; round < 20 && document.title !== expected; round += 1) {
    await new Promise((resolve) => setTimeout(resolve, 10));
  }
  expect(document.title).toBe(expected);
}

describe("useDocumentTitle", () => {
  afterEach(() => {
    document.title = "LabApp";
    vi.restoreAllMocks();
  });

  it("appends the app name to the page title", () => {
    const { rerender } = renderHook(({ title }) => useDocumentTitle(title), {
      initialProps: { title: "Clientes" },
    });

    expect(document.title).toBe("Clientes · LabApp");

    // A change of the argument updates the title on re-render.
    rerender({ title: "Pedidos" });
    expect(document.title).toBe("Pedidos · LabApp");
  });

  it("answers the plain LabApp on an empty title", () => {
    renderHook(() => useDocumentTitle(""));

    expect(document.title).toBe("LabApp");
  });

  it("answers the plain LabApp on a whitespace-only title", () => {
    renderHook(() => useDocumentTitle("   "));

    expect(document.title).toBe("LabApp");
  });

  it("answers the plain LabApp on undefined", () => {
    const { rerender } = renderHook(
      ({ title }) => useDocumentTitle(title),
      { initialProps: { title: "Configuración" as string | undefined } },
    );

    expect(document.title).toBe("Configuración · LabApp");

    rerender({ title: undefined });
    expect(document.title).toBe("LabApp");
  });

  it("restores nothing on unmount", () => {
    const { unmount } = renderHook(() => useDocumentTitle("Resumen"));
    unmount();

    // The title stays as the page left it; the next page sets its own.
    expect(document.title).toBe("Resumen · LabApp");
  });

  it("restores the title when something else writes it, as a soft navigation does", async () => {
    const writeSpy = vi.spyOn(document, "title", "set");
    const view = renderHook(() => useDocumentTitle("Clientes"));
    expect(document.title).toBe("Clientes · LabApp");

    // App Router syncs the title with the route metadata after a soft
    // navigation (a sort click is one), overwriting the page's title.
    document.title = "LabApp";
    await waitForRestored("Clientes · LabApp");

    // The restoration itself is the only extra write: the shared
    // observer settles instead of pushing two titles against each other.
    view.unmount();
    expect(writeSpy.mock.calls.length).toBeLessThan(10);
  });

  it("settles with two hooks mounted at once, as the detail pages mount them", async () => {
    const writeSpy = vi.spyOn(document, "title", "set");
    const outer = renderHook(
      ({ title }) => useDocumentTitle(title),
      { initialProps: { title: "Clientes" } },
    );
    const inner = renderHook(
      ({ title }) => useDocumentTitle(title),
      {
        initialProps: { title: "Cliente Beta Comercial Ltda." },
      },
    );

    // Both effects ran; the last write owns the document and nothing
    // keeps rewriting it. Two observers would ping-pong for ever here.
    expect(document.title).toBe("Cliente Beta Comercial Ltda. · LabApp");
    const writesAfterMounting = writeSpy.mock.calls.length;
    await new Promise((resolve) => setTimeout(resolve, 150));
    expect(writeSpy.mock.calls.length).toBe(writesAfterMounting);

    // A change of the inner title (the customer arrived) writes once
    // more and settles at the new title.
    inner.rerender({ title: "Cliente Acme Industrial S.A." });
    expect(document.title).toBe("Cliente Acme Industrial S.A. · LabApp");
    await new Promise((resolve) => setTimeout(resolve, 150));
    expect(writeSpy.mock.calls.length).toBeLessThan(writesAfterMounting + 5);

    outer.unmount();
    inner.unmount();
    expect(writeSpy.mock.calls.length).toBeLessThan(10);
  });

  it("disconnects the one shared observer when the last hook unmounts", () => {
    const disconnectSpy = vi.spyOn(MutationObserver.prototype, "disconnect");
    const observeSpy = vi.spyOn(MutationObserver.prototype, "observe");

    const first = renderHook(() => useDocumentTitle("Clientes"));
    // The detail pages mount a second call: still exactly one observer.
    const second = renderHook(() => useDocumentTitle("Cliente Acme Industrial S.A."));
    expect(observeSpy).toHaveBeenCalledTimes(1);

    first.unmount();
    expect(disconnectSpy).not.toHaveBeenCalled();

    second.unmount();
    expect(disconnectSpy).toHaveBeenCalledTimes(1);
  });

  it("does not touch the document outside the effect", () => {
    const writeSpy = vi
      .spyOn(document, "title", "set")
      .mockImplementation(() => {});
    try {
      renderHook(() => useDocumentTitle("Clientes"));
      expect(writeSpy).toHaveBeenCalledWith("Clientes · LabApp");
    } finally {
      writeSpy.mockRestore();
    }
  });
});
