"use client";

import {
  Alert,
  Button,
  Field,
  fieldControlProps,
  Link,
  TableScroll,
} from "@/components/ui";
import { useImportCustomers } from "@/features/customers/hooks";
import { ApiRequestError, INTERNAL_ERROR_DETAIL, type ApiProblem } from "@/lib/api";
import { useEffect, useRef, useState } from "react";

/** The fixed sentence of a rejected file (the requirement of task 059). */
const FILE_ERROR_SENTENCE = "El archivo tiene errores. No se importó nada.";

/** The fixed message of a body above the request size limit. */
const FILE_TOO_LARGE_MESSAGE =
  "El archivo es demasiado grande (máximo 100 KB).";

/**
 * Spanish labels of the fields a rejection can name: the five CSV columns,
 * the part `file`, and the whole rows without a column.
 */
const FIELD_LABELS: Record<string, string> = {
  name: "Nombre",
  email: "Email",
  phone: "Teléfono",
  tax_id: "ID fiscal",
  address: "Dirección",
  file: "Archivo",
};

/** Matches `rows[2]` (whole row) and `rows[2].email` (one column). */
const ROW_FIELD_PATTERN = /^rows\[(\d+)\](?:\.(.+))?$/;

/** One row of the error table: the line in the file, the field and why. */
type ImportErrorRow = {
  /** The line number of `rows[N]` in the file, or "—" for a whole-file error. */
  line: string;
  /** The Spanish label of the field the entry reports. */
  field: string;
  /** The message of the API, shown as the API sends it. */
  message: string;
};

/**
 * Maps the `errors[]` entries of a 422 problem to the rows of the error
 * table, in the order the API sends them. The line is the `N` of
 * `rows[N]` or `rows[N].<column>`; a whole-file error (`field: "file"`)
 * has no line.
 */
function mapProblemEntries(problem: ApiProblem): ImportErrorRow[] {
  return (problem.errors ?? []).map((entry) => {
    const match = ROW_FIELD_PATTERN.exec(entry.field);
    if (!match) {
      return {
        line: "—",
        field: FIELD_LABELS[entry.field] ?? entry.field,
        message: entry.message,
      };
    }
    const column = match[2];
    return {
      line: match[1],
      field: column
        ? FIELD_LABELS[column] ?? column
        : "Fila completa",
      message: entry.message,
    };
  });
}

/** The form states the task defines, carried as `data-state` on the form. */
type ImportFormState = "idle" | "loading" | "success" | "error";

/** The classes of the file control, drawn from the form tokens of the theme. */
const FILE_INPUT_CLASSES = [
  "w-full rounded-md border border-control-border bg-surface px-[10px] py-[8px]",
  "text-[15px] text-ink",
  // The browser-drawn "Choose file" button in the voice of the theme.
  "file:mr-3 file:rounded-sm file:border-0 file:bg-accent file:px-3 file:py-1.5",
  "file:text-[13px] file:font-semibold file:text-accent-ink",
].join(" ");

/** The classes of a ledger header cell and a ledger body cell. */
const TABLE_HEAD_CLASSES = [
  "border-b-2 border-ink px-[10px] py-[9px] text-left",
  "text-xs font-medium uppercase tracking-[0.07em] text-muted",
].join(" ");

const TABLE_CELL_CLASSES =
  "border-b border-line px-[10px] py-[9px] text-ink tabular-nums";

/**
 * The customers import form. The server is the only judge of the file: no
 * CSV rule is repeated on the client, the browser sets the multipart
 * headers and the screen shows what the API answers (201 with the count,
 * or the per-row errors of a rejected file). The form is a real form: a
 * submit posts it exactly once while the request is in flight.
 */
export function CustomersImportForm() {
  const importMutation = useImportCustomers();

  const [file, setFile] = useState<File | null>(null);
  const [formState, setFormState] = useState<ImportFormState>("idle");
  const [resultText, setResultText] = useState<string | null>(null);
  const [alertText, setAlertText] = useState<string | null>(null);
  const [errorRows, setErrorRows] = useState<ImportErrorRow[] | null>(null);
  // One increment per failed submit; the focus effect below depends on it.
  const [failureCount, setFailureCount] = useState(0);

  const submitRef = useRef(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const alertRef = useRef<HTMLParagraphElement>(null);

  // After a failure the focus moves to the alert, as the create form does.
  // A repeated failure with the same message still moves the focus because
  // `failureCount` changes.
  useEffect(() => {
    if (formState !== "error") {
      return;
    }
    alertRef.current?.focus();
  }, [failureCount, formState]);

  function clearFile() {
    setFile(null);
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file || submitRef.current) {
      return;
    }

    // A new attempt clears the result and the errors of the previous one.
    setResultText(null);
    setAlertText(null);
    setErrorRows(null);

    submitRef.current = true;
    setFormState("loading");
    try {
      const result = await importMutation.mutateAsync(file);
      // The file was imported: the form returns to idle, the input is
      // cleared and the data lists are already invalidated by the hook.
      setFormState("idle");
      setResultText(
        result.created === 1
          ? "Se importó 1 cliente."
          : `Se importaron ${result.created} clientes.`,
      );
      clearFile();
    } catch (error) {
      setFormState("error");
      setFailureCount((count) => count + 1);
      if (error instanceof ApiRequestError) {
        const problem = error.problem;
        if (problem.status === 413) {
          setAlertText(FILE_TOO_LARGE_MESSAGE);
        } else if (problem.status === 422) {
          // A rejected file: the fixed sentence plus one table row per
          // entry of errors[] (file-level, whole-row and column errors).
          setAlertText(FILE_ERROR_SENTENCE);
          setErrorRows(mapProblemEntries(problem));
        } else {
          // The API's own message (403, 409 CUSTOMER_EMAIL_TAKEN, ...).
          setAlertText(problem.detail);
        }
      } else {
        // Network failure and other unexpected answers.
        setAlertText(INTERNAL_ERROR_DETAIL);
      }
    } finally {
      submitRef.current = false;
    }
  }

  return (
    <div className="w-full max-w-[520px]">
      <h1 data-testid="customers-import-heading">Importar clientes</h1>

      <p
        id="customers-import-help-text"
        data-testid="customers-import-help-text"
        className="mt-2 text-[13px] text-muted"
      >
        El archivo es un CSV en UTF-8 con una fila de encabezado. Las columnas
        son <code>name</code> y <code>email</code> (obligatorias) y{" "}
        <code>phone</code>, <code>tax_id</code> y <code>address</code>{" "}
        (opcionales); admite 200 filas y unos 100 KB como máximo. Si alguna
        fila tiene errores no se importa nada.
      </p>

      {resultText ? (
        <div className="mt-4">
          <p
            role="status"
            data-testid="customers-import-result-text"
            className="rounded-md bg-ok-bg px-[12px] py-[10px] text-[13px] font-medium text-accent"
          >
            {resultText}
          </p>
          <p className="mt-3">
            <Link
              href="/customers"
              testId="customers-import-list-link"
              variant="primary"
            >
              Ver clientes
            </Link>
          </p>
        </div>
      ) : null}

      {alertText ? (
        <div className="mt-4">
          <Alert
            ref={alertRef}
            testId="customers-import-error-alert"
            tabIndex={-1}
          >
            {alertText}
          </Alert>
        </div>
      ) : null}

      {errorRows !== null ? (
        <>
          <TableScroll
            testId="customers-import-errors-region"
            label="Errores del archivo"
            className="mt-4"
          >
            <table
              data-testid="customers-import-errors-table"
              className="min-w-[30rem]"
            >
              <thead>
                <tr>
                  <th scope="col" className={TABLE_HEAD_CLASSES}>Línea</th>
                  <th scope="col" className={TABLE_HEAD_CLASSES}>Campo</th>
                  <th scope="col" className={TABLE_HEAD_CLASSES}>Mensaje</th>
                </tr>
              </thead>
              <tbody>
                {errorRows.map((row, index) => {
                  const n = index + 1;
                  return (
                    <tr
                      key={n}
                      data-testid={`customers-import-error-row-${n}`}
                      className="ledger-row"
                    >
                      <td
                        data-testid={`customers-import-error-line-${n}`}
                        className={`${TABLE_CELL_CLASSES} whitespace-nowrap`}
                      >
                        {row.line}
                      </td>
                      <td
                        data-testid={`customers-import-error-field-${n}`}
                        className={`${TABLE_CELL_CLASSES} whitespace-nowrap`}
                      >
                        {row.field}
                      </td>
                      <td
                        data-testid={`customers-import-error-message-${n}`}
                        className={TABLE_CELL_CLASSES}
                      >
                        {row.message}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </TableScroll>
          {errorRows.length === 100 ? (
            <p
              data-testid="customers-import-truncated-text"
              className="mt-2 text-[13px] text-muted"
            >
              Se muestran los primeros 100 errores.
            </p>
          ) : null}
        </>
      ) : null}

      <form
        data-testid="customers-import-form"
        noValidate
        onSubmit={handleSubmit}
        aria-busy={formState === "loading" ? "true" : undefined}
        data-state={formState}
        className="mt-6 flex flex-col gap-4"
      >
        <Field
          id="customers-import-file-input"
          label="Archivo CSV"
          errorId="customers-import-file-error"
        >
          <input
            type="file"
            accept=".csv,text/csv"
            ref={inputRef}
            {...fieldControlProps(
              "customers-import-file-input",
              undefined,
              "customers-import-file-error",
            )}
            aria-describedby="customers-import-help-text"
            data-testid="customers-import-file-input"
            onChange={(event) =>
              setFile(event.target.files?.[0] ?? null)
            }
            className={FILE_INPUT_CLASSES}
          />
        </Field>
        <div className="flex flex-col items-stretch gap-3 md:flex-row md:items-center">
          <Button
            testId="customers-import-submit-button"
            type="submit"
            disabled={!file}
            loading={formState === "loading"}
            className="w-full md:w-auto"
          >
            Importar
          </Button>
          <Link
            href="/customers"
            testId="customers-import-back-link"
            className="text-center md:text-left"
          >
            Volver a clientes
          </Link>
        </div>
      </form>
    </div>
  );
}
