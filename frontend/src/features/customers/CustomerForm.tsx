"use client";

import { Alert, Button, Input, Link, Textarea } from "@/components/ui";
import { useCreateCustomer, useUpdateCustomer } from "@/features/customers/hooks";
import { ApiRequestError, INTERNAL_ERROR_DETAIL } from "@/lib/api";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import type { Customer } from "./types";

const REQUIRED_MESSAGE = "Este campo es obligatorio.";

export type CustomerFormMode = "create" | "edit";

type CustomerField = "name" | "email" | "phone" | "taxId" | "address";

type CustomerFieldErrors = Partial<Record<CustomerField, string>>;

const FIELD_ORDER: readonly CustomerField[] = [
  "name",
  "email",
  "phone",
  "taxId",
  "address",
];

/** The problem-document field names mapped to the form fields. */
const SERVER_FIELD_BY_CLIENT_FIELD: Record<string, CustomerField> = {
  name: "name",
  email: "email",
  phone: "phone",
  tax_id: "taxId",
  address: "address",
};

type CustomerFormProps =
  | { mode: "create" }
  | {
      mode: "edit";
      /** The customer loaded from the server. */
      customer: Customer;
      /**
       * Increasing signal: when it goes above its mount value the form
       * resets to the current `customer` values ("Recargar datos").
       */
      resetSignal?: number;
      /** Refetches the customer on the page; its presence shows the button. */
      onReload: () => void | Promise<unknown>;
    };

/**
 * Initial values of the form fields. Optional fields are stored as plain
 * strings (`null` becomes "") and only cleared to `null` on submit.
 */
function initialValues(customer?: Customer) {
  return {
    name: customer?.name ?? "",
    email: customer?.email ?? "",
    phone: customer?.phone ?? "",
    taxId: customer?.tax_id ?? "",
    address: customer?.address ?? "",
  };
}

/**
 * Maps the `errors[]` entries of a 422 problem to the matching form fields
 * (`tax_id` shows on the ID fiscal field); `null` when nothing maps.
 */
function mapProblemToFieldErrors(
  problem: ApiRequestError["problem"],
): CustomerFieldErrors | null {
  const mapped: CustomerFieldErrors = {};
  for (const entry of problem.errors ?? []) {
    const field = SERVER_FIELD_BY_CLIENT_FIELD[entry.field];
    if (field && !mapped[field]) {
      mapped[field] = entry.message;
    }
  }
  return FIELD_ORDER.some((field) => mapped[field]) ? mapped : null;
}

/**
 * The create and edit customer form. Only `name` and `email` are checked
 * on the client (required after trimming); every other rule is the
 * server's. The `version` sent on edit is the one captured when the form
 * was initialized or last reset, never the one of a later background
 * refetch, so a refetch while the form is open cannot silently overwrite
 * another user's change.
 */
export function CustomerForm(props: CustomerFormProps) {
  const { mode } = props;
  const customer = props.mode === "edit" ? props.customer : undefined;
  const resetSignal = props.mode === "edit" ? (props.resetSignal ?? 0) : undefined;
  const onReload = props.mode === "edit" ? props.onReload : undefined;

  const router = useRouter();
  const createMutation = useCreateCustomer();
  const updateMutation = useUpdateCustomer();
  const activeMutation = mode === "create" ? createMutation : updateMutation;
  const isSubmitting = activeMutation.isPending;

  const [values, setValues] = useState(() => initialValues(customer));
  const [version, setVersion] = useState(customer?.version ?? 0);
  const [fieldErrors, setFieldErrors] = useState<CustomerFieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [versionConflict, setVersionConflict] = useState(false);
  const [reloadPending, setReloadPending] = useState(false);
  // One increment per failed submit; the focus effect below depends on it.
  const [failureCount, setFailureCount] = useState(0);

  // The pending guard lives in the handler: a state update would not be
  // visible to a second submit processed in the same tick.
  const submittingRef = useRef(false);

  const nameRef = useRef<HTMLInputElement>(null);
  const emailRef = useRef<HTMLInputElement>(null);
  const phoneRef = useRef<HTMLInputElement>(null);
  const taxIdRef = useRef<HTMLInputElement>(null);
  const addressRef = useRef<HTMLTextAreaElement>(null);
  const formAlertRef = useRef<HTMLParagraphElement>(null);

  // The current customer values live in a ref so the reset effect below
  // reads them without depending on every refetch of the query. The sync
  // effect runs before the reset effect in the same commit.
  const customerRef = useRef<Customer | null>(customer ?? null);
  useEffect(() => {
    customerRef.current = customer ?? null;
  });

  // "Recargar datos": one reset per increment of the signal, always from
  // the latest server values; the errors of the failed submit are cleared
  // with it. A background refetch bumps nothing.
  useEffect(() => {
    if (resetSignal === undefined || resetSignal < 1) {
      return;
    }
    const loaded = customerRef.current;
    if (!loaded) {
      return;
    }
    setValues(initialValues(loaded));
    setVersion(loaded.version);
    setFieldErrors({});
    setFormError(null);
    setVersionConflict(false);
  }, [resetSignal]);

  // Focus after a failure: the form-level alert when it is shown,
  // otherwise the first field with an error. Each failed submit bumps
  // `failureCount`, so a failure with the same error strings as before
  // (an unchanged dependency set would skip the effect) still moves the
  // focus.
  useEffect(() => {
    if (!formError && !fieldErrors.name && !fieldErrors.email
      && !fieldErrors.phone && !fieldErrors.taxId && !fieldErrors.address) {
      return;
    }
    if (formError) {
      formAlertRef.current?.focus();
    } else if (fieldErrors.name) {
      nameRef.current?.focus();
    } else if (fieldErrors.email) {
      emailRef.current?.focus();
    } else if (fieldErrors.phone) {
      phoneRef.current?.focus();
    } else if (fieldErrors.taxId) {
      taxIdRef.current?.focus();
    } else {
      addressRef.current?.focus();
    }
  }, [
    failureCount,
    formError,
    fieldErrors.name,
    fieldErrors.email,
    fieldErrors.phone,
    fieldErrors.taxId,
    fieldErrors.address,
  ]);

  async function handleReload() {
    if (!onReload || reloadPending) {
      return;
    }
    setReloadPending(true);
    try {
      await onReload();
    } finally {
      setReloadPending(false);
    }
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submittingRef.current || activeMutation.isPending) {
      return;
    }

    const name = values.name.trim();
    const email = values.email.trim();
    const phone = values.phone.trim();
    const taxId = values.taxId.trim();
    const address = values.address.trim();

    const nextFieldErrors: CustomerFieldErrors = {};
    if (!name) {
      nextFieldErrors.name = REQUIRED_MESSAGE;
    }
    if (!email) {
      nextFieldErrors.email = REQUIRED_MESSAGE;
    }

    if (nextFieldErrors.name || nextFieldErrors.email) {
      setFailureCount((count) => count + 1);
      setFieldErrors(nextFieldErrors);
      setFormError(null);
      setVersionConflict(false);
      return;
    }

    // Each submit clears the errors of the previous one.
    setFieldErrors({});
    setFormError(null);
    setVersionConflict(false);

    submittingRef.current = true;
    try {
      const body = {
        name,
        email,
        phone: phone === "" ? null : phone,
        tax_id: taxId === "" ? null : taxId,
        address: address === "" ? null : address,
      };
      const saved = mode === "create"
        ? await createMutation.mutateAsync(body)
        : await updateMutation.mutateAsync({
            id: customer?.id ?? 0,
            body: { ...body, version },
          });
      router.replace(`/customers/${saved.id}`);
    } catch (error) {
      setFailureCount((count) => count + 1);
      if (error instanceof ApiRequestError) {
        const problem = error.problem;
        if (problem.code === "VERSION_CONFLICT") {
          setFormError(problem.detail);
          setVersionConflict(true);
        } else if (problem.code === "CUSTOMER_EMAIL_TAKEN") {
          setFieldErrors({ email: problem.detail });
        } else {
          const mapped = mapProblemToFieldErrors(problem);
          if (mapped) {
            setFieldErrors(mapped);
          } else {
            setFormError(problem.detail);
          }
        }
      } else {
        setFormError(INTERNAL_ERROR_DETAIL);
      }
    } finally {
      submittingRef.current = false;
    }
  }

  const cancelHref = mode === "create"
    ? "/customers"
    : `/customers/${customer?.id ?? 0}`;

  return (
    <div className="w-full max-w-[520px]">
      <h1 data-testid="customers-form-heading">
        {mode === "create" ? "Nuevo cliente" : "Editar cliente"}
      </h1>

      {formError ? (
        <div className="mt-3">
          <Alert
            ref={formAlertRef}
            testId="customers-form-alert"
            tabIndex={-1}
          >
            {formError}
          </Alert>
          {versionConflict && onReload ? (
            <div className="mt-3">
              <Button
                testId="customers-form-reload-button"
                loading={reloadPending}
                onClick={() => void handleReload()}
              >
                Recargar datos
              </Button>
            </div>
          ) : null}
        </div>
      ) : null}

      <form
        data-testid="customers-customer-form"
        noValidate
        onSubmit={handleSubmit}
        className="mt-6 flex flex-col gap-4"
      >
        <Input
          ref={nameRef}
          id="customers-form-name"
          testId="customers-form-name-input"
          label="Nombre"
          value={values.name}
          onChange={(event) =>
            setValues((current) => ({ ...current, name: event.target.value }))
          }
          error={fieldErrors.name}
        />
        <Input
          ref={emailRef}
          id="customers-form-email"
          testId="customers-form-email-input"
          label="Email"
          type="email"
          value={values.email}
          onChange={(event) =>
            setValues((current) => ({ ...current, email: event.target.value }))
          }
          error={fieldErrors.email}
        />
        <Input
          ref={phoneRef}
          id="customers-form-phone"
          testId="customers-form-phone-input"
          label="Teléfono"
          value={values.phone}
          onChange={(event) =>
            setValues((current) => ({ ...current, phone: event.target.value }))
          }
          error={fieldErrors.phone}
        />
        <Input
          ref={taxIdRef}
          id="customers-form-taxid"
          testId="customers-form-taxid-input"
          label="ID fiscal"
          value={values.taxId}
          onChange={(event) =>
            setValues((current) => ({ ...current, taxId: event.target.value }))
          }
          error={fieldErrors.taxId}
        />
        <Textarea
          ref={addressRef}
          id="customers-form-address"
          testId="customers-form-address-textarea"
          label="Dirección"
          value={values.address}
          onChange={(event) =>
            setValues((current) =>
              ({ ...current, address: event.target.value }),
            )
          }
          error={fieldErrors.address}
        />
        <div className="flex flex-col items-stretch gap-3 md:flex-row md:items-center">
          <Button
            testId="customers-form-submit-button"
            type="submit"
            loading={isSubmitting}
            className="w-full md:w-auto"
          >
            {isSubmitting ? "Guardando…" : "Guardar"}
          </Button>
          <Link
            href={cancelHref}
            testId="customers-form-cancel-link"
            className="text-center md:text-left"
          >
            Cancelar
          </Link>
        </div>
      </form>
    </div>
  );
}
