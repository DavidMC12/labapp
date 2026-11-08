"use client";

import { Button, Link } from "@/components/ui";
import { useDocumentTitle } from "@/lib/useDocumentTitle";

/**
 * The error boundary of every segment under the root layout. The crash
 * itself is never shown: `error.message` and `error.digest` can carry
 * private data, so the page offers only a plain sentence, a retry and the
 * way back home. It logs nothing to the console.
 *
 * Both props come from the boundary; `error` stays unread on purpose.
 */
export default function AppError({
  reset,
}: {
  error: unknown;
  reset: () => void;
}) {
  useDocumentTitle("Algo salió mal");

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 px-4 py-10 text-center">
      <h1 data-testid="app-error-heading">Algo salió mal</h1>
      <p className="text-muted">
        Ocurrió un error inesperado. Puedes intentarlo de nuevo.
      </p>
      <div className="flex flex-wrap items-center justify-center gap-3">
        <Button
          testId="app-error-retry-button"
          onClick={() => reset()}
        >
          Reintentar
        </Button>
        <Link href="/" testId="app-error-home-link" variant="secondary">
          Ir al inicio
        </Link>
      </div>
    </div>
  );
}
