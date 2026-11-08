"use client";

import { Alert, Button, Input, Link, Select } from "@/components/ui";
import {
  useQuery,
  useQueryClient,
  type UseQueryResult,
} from "@tanstack/react-query";
import { useMe } from "@/features/auth/hooks";
import { noteUnauthorized } from "@/features/auth/session";
import { fetchCustomer } from "@/features/customers/api";
import { useCustomers } from "@/features/customers/hooks";
import type { Customer } from "@/features/customers/types";
import { useCreateOrder } from "@/features/orders/hooks";
import { canEditOrders } from "@/features/orders/permissions";
import { parseCustomerIdParam } from "@/features/orders/params";
import { ApiRequestError, INTERNAL_ERROR_DETAIL } from "@/lib/api";
import { useDocumentTitle } from "@/lib/useDocumentTitle";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";


/**
 * The create order page: a customer search and a select of the active
 * customers (up to 20 per page, the page size of the API), then the form
 * that posts the draft. The search is its own form, never nested inside
 * the one that submits. The url can only be read inside a Suspense
 * boundary (`useSearchParams` falls back to the static shell of the page
 * below it), so the content lives here and the default export wraps it,
 * with the `customer_id` preselection.
 */
export default function CustomerCreatePage() {
  useDocumentTitle("Nuevo pedido");

  return (
    <Suspense
      fallback={
        <p
          role="status"
          data-testid="orders-form-loading-status"
          aria-busy="true"
          className="text-muted"
        >
          Cargando…
        </p>
      }
    >
      <CustomerCreateContent />
    </Suspense>
  );
}

/**
 * One customer for the preselection, or a query that never runs when the
 * url carries no customer. It shares the cache entry of the customers
 * detail screen, and a 401 ends the session exactly as the detail hook
 * does (`noteUnauthorized`).
 */
function usePresetCustomer(
  id: number | null,
): UseQueryResult<Customer, ApiRequestError> {
  const queryClient = useQueryClient();

  return useQuery<Customer, ApiRequestError>({
    queryKey: ["customers", "detail", id],
    queryFn: async () => {
      const customerId = id as number;
      try {
        return await fetchCustomer(customerId);
      } catch (error) {
        noteUnauthorized(error, queryClient);
        throw error;
      }
    },
    enabled: id !== null,
    retry: false,
  });
}

function CustomerCreateContent() {
  const me = useMe();
  const router = useRouter();
  const create = useCreateOrder();

  // The preselection: a strict parse of the `customer_id` of the url, and
  // the loading of that one customer.
  const presetCustomerId = parseCustomerIdParam(
    useSearchParams().get("customer_id"),
  );
  const preset = usePresetCustomer(presetCustomerId);

  // The query of the picker: page 1, active customers only. `q` changes
  // when the search form is submitted; nothing is applied while typing.
  const [pickerQ, setPickerQ] = useState("");
  const [pickerInput, setPickerInput] = useState("");
  const customers = useCustomers({ page: 1, q: pickerQ || undefined, status: "active" });

  const [customerId, setCustomerId] = useState("");
  const [selectError, setSelectError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  // One increment per failed submit; the focus effect below depends on it.
  const [failureCount, setFailureCount] = useState(0);
  const submittingRef = useRef(false);

  const formAlertRef = useRef<HTMLParagraphElement>(null);

  // The preselection is applied once: this state remembers the preset id
  // that already set `customerId`, so a later refetch of the customer
  // (or any other re-render) never overwrites a choice the user made.
  const [appliedPresetId, setAppliedPresetId] = useState<number | null>(null);

  // B3: the choice never holds an id the select does not show. When a new
  // search (or a refetch) brings a different list of options, the
  // selection goes back to the placeholder. The reset runs during render —
  // the "adjust state when a dependency changes" pattern of the
  // customers list — instead of setting state inside an effect. The one
  // exception is the preset customer: while the choice is the preselected
  // one, the select shows it as an extra option below (it came from the
  // url, ahead of the search).
  const [lastData, setLastData] = useState<typeof customers.data>(undefined);
  const presetData = preset.isSuccess ? preset.data : null;
  const presetHoldsChoice =
    presetData !== null
    && presetData.status === "active"
    && customerId === String(presetData.id);
  if (customers.data !== lastData) {
    setLastData(customers.data);
    const items = customers.data?.items ?? [];
    if (
      customerId !== ""
      && !items.some((candidate) => String(candidate.id) === customerId)
      && !presetHoldsChoice
    ) {
      setCustomerId("");
    }
  }

  // The application of the preselection: once the url's customer arrives
  // and is active, it becomes the choice. Runs during render, guarded by
  // `appliedPresetId`: an inactive (or missing) customer is never chosen,
  // and it stays applied even when the customer refetches.
  if (
    presetCustomerId !== null
    && appliedPresetId !== presetCustomerId
    && presetData !== null
    && presetData.status === "active"
  ) {
    setAppliedPresetId(presetCustomerId);
    setCustomerId(String(presetData.id));
  }

  // Focus after a failure: the form-level alert when it is shown,
  // otherwise the select. Each failed submit bumps `failureCount`, so a
  // failure with the same messages as before still moves the focus.
  useEffect(() => {
    if (!formError && !selectError) {
      return;
    }
    if (formError) {
      formAlertRef.current?.focus();
    } else {
      document.getElementById("orders-form-customer")?.focus();
    }
  }, [failureCount, formError, selectError]);

  if (me.isPending) {
    return (
      <p
        role="status"
        data-testid="orders-form-loading-status"
        aria-busy="true"
        className="text-muted"
      >
        Cargando…
      </p>
    );
  }

  const user = me.data;

  if (user && !canEditOrders(user.role)) {
    return (
      <Alert testId="orders-form-forbidden-alert">
        No tienes permiso para realizar esta acción.
      </Alert>
    );
  }

  function pickerProblemDetail(): string {
    if (customers.error instanceof ApiRequestError) {
      return customers.error.problem.detail;
    }
    return INTERNAL_ERROR_DETAIL;
  }

  async function handleCustomerSearch(
    event: React.FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();
    setPickerQ(pickerInput.trim());
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submittingRef.current || create.isPending || customerId === "") {
      return;
    }

    // Each submit clears the errors of the previous one.
    setSelectError(null);
    setFormError(null);

    submittingRef.current = true;
    try {
      const order = await create.mutateAsync(Number(customerId));
      // The login-like navigation replaces the creation page: the detail
      // of the new draft comes from the cache write of the mutation.
      router.replace(`/orders/${order.id}`);
    } catch (error) {
      setFailureCount((count) => count + 1);
      if (error instanceof ApiRequestError) {
        const problem = error.problem;
        // The field of a body error is exactly `customer_id` here (the
        // corrected spec, S1). A 422 on it shows on the select;
        // CUSTOMER_INACTIVE shows its detail on the select too.
        const fieldError = problem.errors?.find(
          (entry) => entry.field === "customer_id",
        );
        if (fieldError) {
          setSelectError(fieldError.message);
        } else if (problem.code === "CUSTOMER_INACTIVE") {
          setSelectError(problem.detail);
        } else {
          setFormError(problem.detail);
        }
      } else {
        setFormError(INTERNAL_ERROR_DETAIL);
      }
    } finally {
      submittingRef.current = false;
    }
  }

  const pickerItems = customers.isSuccess ? customers.data.items : [];

  // Derived states of the preselection.
  const presetLoading = preset.isLoading;
  // While the choice is the preset one (or the list already shows the
  // customer), the select keeps an option for it. An active preset is
  // shown the moment it arrives; a later choice of another customer (or a
  // reset) removes it.
  const presetExtra =
    presetData !== null
    && presetData.status === "active"
    && customerId === String(presetData.id)
    && !pickerItems.some((candidate) => candidate.id === presetData.id)
      ? { value: String(presetData.id), name: presetData.name }
      : null;
  // A preset customer that arrived but cannot receive an order (inactive,
  // unknown or any failed load): the notice explains it. It never blocks
  // the picker; the user can pick from the list or search as usual.
  const presetUnavailable =
    presetCustomerId !== null
    && !presetLoading
    && (preset.isError || (presetData !== null && presetData.status !== "active"));

  return (
    <div>
      <h1 data-testid="orders-form-heading">Nuevo pedido</h1>

      {formError ? (
        <div className="mt-3">
          <Alert
            ref={formAlertRef}
            testId="orders-form-alert"
            tabIndex={-1}
          >
            {formError}
          </Alert>
        </div>
      ) : null}

      <form
        data-testid="orders-form-customersearch-form"
        onSubmit={handleCustomerSearch}
        className="mt-6 flex flex-wrap items-end gap-3"
      >
        <Input
          id="orders-form-customersearch"
          testId="orders-form-customersearch-input"
          label="Buscar cliente"
          value={pickerInput}
          onChange={(event) => setPickerInput(event.target.value)}
        />
        <Button
          testId="orders-form-customersearch-button"
          type="submit"
          variant="secondary"
        >
          Buscar
        </Button>
      </form>

      {customers.isPending ? (
        <p
          role="status"
          data-testid="orders-form-customer-loading-status"
          aria-busy="true"
          className="mt-4 text-muted"
        >
          Buscando clientes…
        </p>
      ) : customers.isError ? (
        <div className="mt-4">
          <Alert testId="orders-form-error-alert">
            {pickerProblemDetail()}
          </Alert>
          <div className="mt-3">
            <Button
              testId="orders-form-retry-button"
              onClick={() => void customers.refetch()}
            >
              Reintentar
            </Button>
          </div>
        </div>
      ) : pickerItems.length === 0 ? (
        <p
          role="status"
          data-testid="orders-form-customer-empty-status"
          className="mt-4 text-muted"
        >
          No hay clientes activos que coincidan.
        </p>
      ) : null}

      {presetUnavailable ? (
        <p
          role="status"
          data-testid="orders-form-presetcustomer-status"
          className="mt-4 text-muted"
        >
          El cliente indicado no está disponible para nuevos pedidos.
        </p>
      ) : null}

      <form
        data-testid="orders-customer-form"
        noValidate
        onSubmit={handleSubmit}
        className="mt-6 flex w-full max-w-[520px] flex-col gap-4"
      >
        <Select
          id="orders-form-customer"
          testId="orders-form-customer-select"
          label="Cliente"
          value={customerId}
          onChange={(event) => setCustomerId(event.target.value)}
          error={selectError ?? undefined}
          disabled={presetLoading}
        >
          {/* The placeholder of the corrected review (B3): disabled, so
              the submit cannot send an empty customer id. */}
          <option value="" disabled>
            Elige un cliente
          </option>
          {/* The customer of the url while it is in the air: the choice
              stays empty, nothing can be picked and the submit stays
              disabled until the customer arrives. */}
          {presetLoading && presetCustomerId !== null ? (
            <option value={String(presetCustomerId)} disabled>
              Cargando cliente…
            </option>
          ) : null}
          {pickerItems.map((candidate) => (
            <option key={candidate.id} value={candidate.id}>
              {candidate.name}
            </option>
          ))}
          {/* The preselected customer, when it is not among the first
              twenty of the picker: one data-bearing extra option, no
              duplicate. */}
          {presetExtra ? (
            <option value={presetExtra.value}>{presetExtra.name}</option>
          ) : null}
        </Select>
        <p
          data-testid="orders-form-customer-text"
          className="text-[13px] text-muted"
        >
          Se muestran hasta 20 clientes activos; usa la búsqueda para
          encontrar otro.
        </p>
        <div className="flex flex-col items-stretch gap-3 md:flex-row md:items-center">
          <Button
            testId="orders-form-submit-button"
            type="submit"
            loading={create.isPending}
            disabled={customerId === ""}
            className="w-full md:w-auto"
          >
            Crear pedido
          </Button>
          <Link
            href="/orders"
            testId="orders-form-cancel-link"
            className="text-center md:text-left"
          >
            Cancelar
          </Link>
        </div>
      </form>
    </div>
  );
}
