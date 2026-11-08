import { useEffect, useRef, useState } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ConfirmDialog } from "./ConfirmDialog";
import { installDialogStub } from "@/test/dialog";

type Props = Parameters<typeof ConfirmDialog>[0];

function baseProps(overrides: Partial<Props> = {}): Props {
  return {
    open: true,
    title: "¿Desactivar a Distribuidora Delta?",
    children: "No podrá recibir pedidos nuevos.",
    confirmLabel: "Sí, desactivar",
    onConfirm: vi.fn(),
    onCancel: vi.fn(),
    titleId: "customers-deactivate-title",
    messageId: "customers-deactivate-message",
    testId: "customers-deactivate-confirm-dialog",
    titleTestId: "customers-deactivate-title-heading",
    messageTestId: "customers-deactivate-message-text",
    confirmTestId: "customers-deactivate-confirm-button",
    cancelTestId: "customers-deactivate-back-button",
    ...overrides,
  };
}

beforeEach(() => {
  installDialogStub();
  document.title = "LabApp";
});

function dialogElement() {
  return screen.getByTestId(
    "customers-deactivate-confirm-dialog",
  ) as HTMLDialogElement;
}

describe("ConfirmDialog", () => {
  it("renders title, message and buttons with their ids when open", () => {
    render(<ConfirmDialog {...baseProps()} />);

    const dialog = dialogElement();
    expect(dialog).toHaveAttribute("open");

    expect(screen.getByTestId("customers-deactivate-title-heading"))
      .toHaveTextContent("¿Desactivar a Distribuidora Delta?");
    expect(screen.getByTestId("customers-deactivate-message-text"))
      .toHaveTextContent("No podrá recibir pedidos nuevos.");
    expect(screen.getByTestId("customers-deactivate-confirm-button"))
      .toHaveTextContent("Sí, desactivar");
    // The default label of the way out.
    expect(screen.getByTestId("customers-deactivate-back-button"))
      .toHaveTextContent("Volver");

    // The dialog names its title and its description.
    expect(dialog).toHaveAttribute(
      "aria-labelledby",
      "customers-deactivate-title",
    );
    expect(dialog).toHaveAttribute(
      "aria-describedby",
      "customers-deactivate-message",
    );
  });

  it("stays closed while open is false", () => {
    render(<ConfirmDialog {...baseProps({ open: false })} />);

    expect(dialogElement()).not.toHaveAttribute("open");
  });

  it("answers confirm and cancel from the buttons", async () => {
    const props = baseProps();
    render(<ConfirmDialog {...props} />);
    const user = userEvent.setup();

    await user.click(screen.getByTestId("customers-deactivate-confirm-button"));
    expect(props.onConfirm).toHaveBeenCalledTimes(1);
    expect(props.onCancel).not.toHaveBeenCalled();

    await user.click(screen.getByTestId("customers-deactivate-back-button"));
    expect(props.onCancel).toHaveBeenCalledTimes(1);
    expect(props.onConfirm).toHaveBeenCalledTimes(1);
  });

  it("answers the cancel event with onCancel and never closes by itself", () => {
    const props = baseProps();
    render(<ConfirmDialog {...props} />);
    const dialog = dialogElement();

    // The cancel event that the Escape key produces (jsdom does not
    // synthesize it, the pages dispatch it the same way).
    dialog.dispatchEvent(new Event("cancel", { bubbles: true }));
    expect(props.onCancel).toHaveBeenCalledTimes(1);
    // The native default is prevented: only the caller closes it.
    expect(dialog).toHaveAttribute("open");
  });

  it("answers a click on the backdrop like the Escape key", async () => {
    const props = baseProps();
    render(<ConfirmDialog {...props} />);
    const user = userEvent.setup();

    // A click whose target is the dialog element is the backdrop.
    await user.click(dialogElement());
    expect(props.onCancel).toHaveBeenCalledTimes(1);
    expect(props.onConfirm).not.toHaveBeenCalled();
  });

  it("does nothing for the backdrop or the Escape while pending", () => {
    const props = baseProps({ pending: true });
    render(<ConfirmDialog {...props} />);
    const dialog = dialogElement();

    dialog.dispatchEvent(new Event("cancel", { bubbles: true }));
    expect(props.onCancel).not.toHaveBeenCalled();
    // The dialog cannot close by itself while the request runs; the
    // caller closes it when the request ends.
    expect(dialog).toHaveAttribute("open");
  });

  it("disables both buttons while pending and marks the confirm busy", () => {
    render(<ConfirmDialog {...baseProps({ pending: true })} />);

    const confirm = screen.getByTestId("customers-deactivate-confirm-button");
    expect(confirm).toBeDisabled();
    expect(confirm).toHaveAttribute("data-state", "loading");
    expect(confirm).toHaveAttribute("aria-busy", "true");
    expect(
      screen.getByTestId("customers-deactivate-back-button"),
    ).toBeDisabled();
  });

  it("gives the first focus to the Volver button, never the confirm", () => {
    render(<ConfirmDialog {...baseProps()} />);

    expect(document.activeElement).toHaveAttribute(
      "data-testid",
      "customers-deactivate-back-button",
    );
  });

  it("returns the focus to the opener when open turns false", async () => {
    // The pattern the two pages have: the click leaves the focus on the
    // button that opened the dialog, so closing has to hand the focus
    // back there exactly.
    function Page() {
      const [open, setOpen] = useState(false);
      const openerRef = useRef<HTMLButtonElement>(null);
      useEffect(() => {
        openerRef.current?.focus();
      }, []);
      return (
        <div>
          <button
            type="button"
            ref={openerRef}
            data-testid="orders-detail-cancel-button"
            onClick={() => setOpen(true)}
          >
            Cancelar pedido
          </button>
          <ConfirmDialog
            {...baseProps({ open, onCancel: () => setOpen(false) })}
          />
        </div>
      );
    }

    render(<Page />);
    const opener = screen.getByTestId("orders-detail-cancel-button");
    expect(document.activeElement).toBe(opener);

    const user = userEvent.setup();
    await user.click(opener);
    await waitFor(() => {
      expect(dialogElement()).toHaveAttribute("open");
    });
    expect(document.activeElement).toHaveAttribute(
      "data-testid",
      "customers-deactivate-back-button",
    );

    // The way out closes it and the focus is back on the opener.
    await user.click(screen.getByTestId("customers-deactivate-back-button"));
    await waitFor(() => {
      expect(dialogElement()).not.toHaveAttribute("open");
    });
    expect(document.activeElement).toBe(opener);
  });
});
