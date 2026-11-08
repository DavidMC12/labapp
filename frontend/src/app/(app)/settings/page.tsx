"use client";

import { Alert, Button, Input } from "@/components/ui";
import { useMe } from "@/features/auth/hooks";
import { useSettings, useUpdateTaxRate } from "@/features/settings/hooks";
import { canChangeTaxRate } from "@/features/settings/permissions";
import { ApiRequestError, INTERNAL_ERROR_DETAIL } from "@/lib/api";
import { useDocumentTitle } from "@/lib/useDocumentTitle";
import { useEffect, useRef, useState } from "react";

/**
 * The "Configuración" screen (docs/SPEC.md section 2: only an Admin can
 * change the tax rate). Every role sees the current rate; the form is
 * offered only to the Admin and the server remains the authority.
 *
 * The screen adds no validation of its own: the raw value is sent exactly
 * as typed and every server answer is shown as it comes, so the rules of
 * the spec (format, range, permission) are asserted by the API itself.
 */
export default function SettingsPage() {
  useDocumentTitle("Configuración");
  const me = useMe();
  const settings = useSettings();
  const updateMutation = useUpdateTaxRate();
  const isSubmitting = updateMutation.isPending;

  // The input keeps exactly what the user typed. It is prefilled once,
  // the first time the current settings arrive (the documented
  // "adjust state when its dependencies change" pattern); a later
  // refetch never overwrites an edit in progress, and on a success the
  // answer sets the value, so the state only ever goes from null to a
  // value.
  const [taxRate, setTaxRate] = useState<string | null>(null);
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [savedMessage, setSavedMessage] = useState<string | null>(null);

  const settingsRate = settings.data?.tax_rate ?? null;
  if (taxRate === null && settingsRate !== null) {
    setTaxRate(settingsRate);
  }

  // The pending guard lives in the handler: a state update would not be
  // visible to a second submit processed in the same tick.
  const submittingRef = useRef(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const formAlertRef = useRef<HTMLParagraphElement>(null);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submittingRef.current || updateMutation.isPending) {
      return;
    }

    // Each submit clears the errors and the success of the previous one.
    setFieldError(null);
    setFormError(null);
    setSavedMessage(null);

    submittingRef.current = true;
    try {
      // The string exactly as typed: never trimmed, never parsed.
      const saved = await updateMutation.mutateAsync(taxRate ?? "");
      setTaxRate(saved.tax_rate);
      setSavedMessage(`Impuesto actualizado a ${saved.tax_rate} %.`);
    } catch (error) {
      if (error instanceof ApiRequestError) {
        // The field errors of tax_rate go next to the field (the
        // message of the answer); everything else goes to the form
        // alert with its detail.
        const fieldProblem = (error.problem.errors ?? []).find(
          (entry) => entry.field === "tax_rate",
        );
        if (fieldProblem) {
          setFieldError(fieldProblem.message);
        } else {
          setFormError(error.problem.detail);
        }
      } else {
        setFormError(INTERNAL_ERROR_DETAIL);
      }
    } finally {
      submittingRef.current = false;
    }
  }

  // Focus after a failure: the form alert when it is shown, otherwise the
  // input. Runs after the DOM update, because the alert node may not
  // exist yet when the rejection is handled.
  useEffect(() => {
    if (formError) {
      formAlertRef.current?.focus();
    } else if (fieldError) {
      inputRef.current?.focus();
    }
  }, [formError, fieldError]);

  if (me.isPending) {
    return (
      <p
        role="status"
        data-testid="settings-page-loading-status"
        aria-busy="true"
        className="text-muted"
      >
        Cargando…
      </p>
    );
  }

  // The load error comes first: it has no data, so a check on the data
  // would render the loading status for ever.
  if (settings.isError) {
    const problemDetail = settings.error instanceof ApiRequestError
      ? settings.error.problem.detail
      : INTERNAL_ERROR_DETAIL;

    return (
      <div>
        <h1 data-testid="settings-page-heading">Configuración</h1>
        <div className="mt-6">
          <Alert testId="settings-page-error-alert">{problemDetail}</Alert>
          <div className="mt-3">
            <Button
              testId="settings-page-retry-button"
              onClick={() => void settings.refetch()}
            >
              Reintentar
            </Button>
          </div>
        </div>
      </div>
    );
  }

  if (settings.isPending) {
    return (
      <p
        role="status"
        data-testid="settings-page-loading-status"
        aria-busy="true"
        className="text-muted"
      >
        Cargando configuración…
      </p>
    );
  }

  if (!settings.data) {
    // Unreachable with the two checks above; keeps `settings.data` typed.
    return null;
  }

  const user = me.data;
  const canChange = user ? canChangeTaxRate(user.role) : false;

  return (
    <div>
      <h1 data-testid="settings-page-heading">Configuración</h1>

      <section
        aria-labelledby="settings-taxrate-heading"
        className="mt-6 max-w-[520px] rounded-lg border border-line bg-surface p-5"
      >
        <h2
          id="settings-taxrate-heading"
          data-testid="settings-taxrate-heading"
          className="text-[15px]"
        >
          Impuesto
        </h2>

        {/* The rate as the server stores it, plus the unit: "10.00 %". */}
        <p
          data-testid="settings-taxrate-current-text"
          className="mt-2 text-muted tabular-nums"
        >
          {`${settings.data.tax_rate} %`}
        </p>

        {canChange ? (
          <>
            {formError ? (
              <div className="mt-3">
                <Alert
                  ref={formAlertRef}
                  testId="settings-taxrate-alert"
                  tabIndex={-1}
                >
                  {formError}
                </Alert>
              </div>
            ) : null}

            <form
              data-testid="settings-taxrate-form"
              noValidate
              aria-busy={isSubmitting ? "true" : undefined}
              onSubmit={handleSubmit}
              className="mt-4 flex flex-col items-start gap-4"
            >
              <Input
                ref={inputRef}
                id="settings-taxrate"
                testId="settings-taxrate-input"
                label="Tasa de impuesto (%)"
                type="text"
                inputMode="decimal"
                value={taxRate ?? ""}
                onChange={(event) => setTaxRate(event.target.value)}
                error={fieldError ?? undefined}
                className="w-full md:w-52"
              />
              <Button
                testId="settings-taxrate-save-button"
                type="submit"
                loading={isSubmitting}
              >
                {isSubmitting ? "Guardando…" : "Guardar"}
              </Button>
            </form>

            {savedMessage ? (
              <p
                role="status"
                data-testid="settings-taxrate-success-status"
                className="mt-4 text-[13px] font-medium"
              >
                {savedMessage}
              </p>
            ) : null}
          </>
        ) : (
          <p
            data-testid="settings-taxrate-readonly-text"
            className="mt-3 text-[13px] text-muted"
          >
            Solo un administrador puede cambiar el impuesto.
          </p>
        )}
      </section>
    </div>
  );
}
