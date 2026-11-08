import { renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useDocumentTitle } from "./useDocumentTitle";

describe("useDocumentTitle", () => {
  afterEach(() => {
    document.title = "LabApp";
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
