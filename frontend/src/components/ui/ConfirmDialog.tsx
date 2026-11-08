"use client";

import type { ReactNode, Ref } from "react";
import { Button } from "./Button";
import type { TestId } from "@/lib/testid";
import { useEffect, useRef } from "react";

const DIALOG_CLASSES: string = [
  "m-auto w-[calc(100%-32px)] max-w-[440px]",
  "rounded-lg border border-line bg-surface p-5",
  "text-ink",
].join(" ");

/** The ref of the `<dialog>` element, forwarded or owned. */
function asRefObject(
  ref: Ref<HTMLDialogElement> | undefined,
  internal: React.RefObject<HTMLDialogElement | null>,
): React.RefObject<HTMLDialogElement | null> {
  // React 19 delivers the ref prop here as the object form; a callback
  // ref is not used by the callers of this component.
  if (ref && typeof ref === "object" && "current" in ref) {
    return ref;
  }
  return internal;
}

type ConfirmDialogProps = {
  /** Controlled visibility: true calls `showModal()`, false closes. */
  open: boolean;
  title: string;
  /** The message of the consequence of the action. */
  children: ReactNode;
  confirmLabel: string;
  /** Defaults to "Volver": the quiet way out that receives the focus. */
  cancelLabel?: string;
  /** Disables both buttons and shows the confirm as loading. */
  pending?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  /** The test ids of the four parts (typed `TestId`s). */
  testId: TestId;
  titleTestId: TestId;
  messageTestId: TestId;
  confirmTestId: TestId;
  cancelTestId: TestId;
  /** DOM ids for `aria-labelledby` and `aria-describedby`. */
  titleId: string;
  messageId: string;
  /** React 19 forwards `ref` as a prop. */
  ref?: Ref<HTMLDialogElement>;
};

/**
 * The confirmation dialog of the destructive actions, on the native
 * `<dialog>` element and its `showModal()`. A controlled component: the
 * caller owns `open`, the component moves the element with it.
 *
 * - The Escape key (`cancel` event) and a click on the backdrop both
 *   answer `onCancel` — never a close by themselves, and neither runs
 *   while `pending`: the dialog waits for the request to end.
 * - The first focus is the "Volver" button, never the destructive one.
 * - Closing gives the focus back to the element that had it when the
 *   dialog opened (the opener), which the native behavior does with a
 *   real `close()` and the component reproduces for the tests.
 */
export function ConfirmDialog({
  open,
  title,
  children,
  confirmLabel,
  cancelLabel = "Volver",
  pending = false,
  onConfirm,
  onCancel,
  testId,
  titleTestId,
  messageTestId,
  confirmTestId,
  cancelTestId,
  titleId,
  messageId,
  ref: dialogRef,
}: ConfirmDialogProps) {
  const internalRef = useRef<HTMLDialogElement>(null);
  const cancelRef = useRef<HTMLButtonElement>(null);
  const openerRef = useRef<HTMLElement | null>(null);

  const dialog = asRefObject(dialogRef, internalRef);

  useEffect(() => {
    const element = dialog.current;
    if (element === null) {
      return;
    }
    if (open) {
      // The element that had the focus before the dialog joined the top
      // layer; closing hands it back (the native behavior).
      openerRef.current = document.activeElement as HTMLElement | null;
      element.showModal();
      cancelRef.current?.focus();
    } else {
      element.close();
      const opener = openerRef.current;
      openerRef.current = null;
      opener?.focus();
    }
    // Only `open` drives the element; the callbacks are fresh closures.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  function handleCancel(event: React.SyntheticEvent) {
    // The native close never happens by itself: the component answers
    // with `onCancel` while the request is not pending, and does nothing
    // while it is (the dialog closes when the request ends).
    event.preventDefault();
    if (!pending) {
      onCancel();
    }
  }

  function handleBackdropClick(event: React.MouseEvent<HTMLDialogElement>) {
    // A click that reaches the dialog itself went through the backdrop;
    // a click inside hits the title, the message or the buttons first.
    if (event.target === dialog.current) {
      handleCancel(event);
    }
  }

  return (
    <dialog
      ref={dialog}
      data-testid={testId}
      aria-labelledby={titleId}
      aria-describedby={messageId}
      onCancel={handleCancel}
      onClick={handleBackdropClick}
      className={DIALOG_CLASSES}
    >
      <h2 id={titleId} data-testid={titleTestId} className="font-serif">
        {title}
      </h2>
      <p id={messageId} data-testid={messageTestId} className="mt-2">
        {children}
      </p>
      <div className="mt-5 flex flex-wrap items-center justify-end gap-3">
        <Button
          ref={cancelRef}
          testId={cancelTestId}
          variant="secondary"
          disabled={pending}
          onClick={onCancel}
        >
          {cancelLabel}
        </Button>
        <Button
          testId={confirmTestId}
          variant="danger"
          loading={pending}
          onClick={onConfirm}
        >
          {confirmLabel}
        </Button>
      </div>
    </dialog>
  );
}
