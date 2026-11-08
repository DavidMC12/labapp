"use client";

import { Alert, Input, ThemeSelect } from "@/components/ui";
import { Button } from "@/components/ui";
import { LedgerMark } from "@/components/LedgerMark";
import { useLogin } from "@/features/auth/hooks";
import { DEMO_PASSWORD_TEXT, DEMO_USERS } from "@/features/auth/demo";
import { roleLabel } from "@/features/auth/types";
import { ApiRequestError, INTERNAL_ERROR_DETAIL } from "@/lib/api";
import { useDocumentTitle } from "@/lib/useDocumentTitle";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";

const REQUIRED_MESSAGE = "Este campo es obligatorio.";

type LoginField = "email" | "password";

type LoginFieldErrors = Partial<Record<LoginField, string>>;

/**
 * The url can only be read inside a Suspense boundary (`useSearchParams`
 * falls back to the static shell of the page below it), so the form lives
 * here and the default export wraps it.
 */
export default function LoginPage() {
  useDocumentTitle("Iniciar sesión");

  return (
    <Suspense
      fallback={
        <p
          role="status"
          data-testid="auth-login-loading-status"
          aria-busy="true"
          className="min-h-screen p-4 text-muted"
        >
          Cargando…
        </p>
      }
    >
      <LoginPageContent />
    </Suspense>
  );
}

function LoginPageContent() {
  const router = useRouter();
  const login = useLogin();
  const searchParams = useSearchParams();

  // The reason of the visit comes from the url of the redirect of the
  // shell (`/login?expired=1`); a login that succeeds resolves it, so the
  // notice must not show up again after that.
  const [showExpiredNotice, setShowExpiredNotice] = useState(
    () => searchParams.get("expired") === "1",
  );

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<LoginFieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);

  // The pending guard lives in the handler: a state update would not be
  // visible to a second submit processed in the same tick.
  const submittingRef = useRef(false);

  const emailRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);
  const formAlertRef = useRef<HTMLParagraphElement>(null);

  // Focus after a failure: the form-level alert when it is shown,
  // otherwise the first field with an error. Runs after the DOM update,
  // because the alert node may not exist yet when the rejection is handled.
  useEffect(() => {
    if (!formError && !fieldErrors.email && !fieldErrors.password) {
      return;
    }
    if (formError) {
      formAlertRef.current?.focus();
    } else if (fieldErrors.email) {
      emailRef.current?.focus();
    } else {
      passwordRef.current?.focus();
    }
  }, [formError, fieldErrors.email, fieldErrors.password]);

  function mapProblemToFieldErrors(
    problem: ApiRequestError["problem"],
  ): LoginFieldErrors | null {
    const mapped: LoginFieldErrors = {};
    for (const entry of problem.errors ?? []) {
      if ((entry.field === "email" || entry.field === "password")
        && !mapped[entry.field]) {
        mapped[entry.field] = entry.message;
      }
    }
    return mapped.email || mapped.password ? mapped : null;
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submittingRef.current || login.isPending) {
      return;
    }

    // The email is trimmed before every check, so a whitespace-only email
    // counts as empty; the password is checked as typed.
    const trimmedEmail = email.trim();
    const nextFieldErrors: LoginFieldErrors = {};
    if (!trimmedEmail) {
      nextFieldErrors.email = REQUIRED_MESSAGE;
    }
    if (!password) {
      nextFieldErrors.password = REQUIRED_MESSAGE;
    }

    if (nextFieldErrors.email || nextFieldErrors.password) {
      setFieldErrors(nextFieldErrors);
      setFormError(null);
      return;
    }

    // Each submit clears the errors of the previous one.
    setFieldErrors({});
    setFormError(null);

    submittingRef.current = true;
    try {
      await login.mutateAsync({ email: trimmedEmail, password });
      // The expired-session notice is resolved once the session is back.
      setShowExpiredNotice(false);
      // The login page must not stay in the history.
      router.replace("/");
    } catch (error) {
      if (error instanceof ApiRequestError) {
        const mapped = mapProblemToFieldErrors(error.problem);
        if (mapped) {
          setFieldErrors(mapped);
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

  const isSubmitting = login.isPending;

  return (
    <>
      {/*
       * The first focusable element of the page (WCAG 2.4.1 bypass
       * blocks): hidden until it receives focus, then a solid chip. It
       * jumps to the main landmark of the login, which the other list
       * screens reach through the shell's own link.
       */}
      <a
        href="#main-content"
        data-testid="auth-login-skip-link"
        className={[
          "sr-only focus:not-sr-only",
          "focus:fixed focus:left-2 focus:top-2 focus:z-50",
          "focus:rounded-md focus:bg-surface focus:px-3 focus:py-2",
          "focus:font-medium focus:text-ink",
        ].join(" ")}
      >
        Saltar al contenido
      </a>
      {/* The main landmark the login page did not have. */}
      <main
        id="main-content"
        tabIndex={-1}
        className="min-h-screen md:grid md:grid-cols-2"
      >
        {/*
         * The rail panel of the login: the brand and the theme's sentence.
         * Hidden below 768px, where the form takes the whole width.
         */}
        <aside className="hidden bg-rail text-rail-ink md:flex md:flex-col md:justify-between md:p-10">
          <div>
            <p className="flex items-center gap-2 font-serif text-lg font-semibold">
              <LedgerMark />
              LabApp
            </p>
          </div>
          <div className="max-w-[420px]">
            <p
              data-testid="auth-login-tagline-text"
              className="font-serif text-[32px] leading-[1.2]"
            >
              Del pedido al cobro, sin perder el hilo.
            </p>
            <p
              data-testid="auth-login-notice-text"
              className="mt-3 text-[13px] text-rail-muted"
            >
              Demostración pública. Los datos se reinician cada noche.
            </p>
          </div>
        </aside>

        {/*
         * The form column: heading, error alert, form and demo users.
         */}
        <div className="flex min-w-0 items-center justify-center px-4 py-10 md:px-10">
          <div className="w-full max-w-[440px]">
            {/*
             * The theme selector sits at the top right of the form column,
             * above the heading.
             */}
            <div className="flex justify-end">
              <div className="w-40">
                <ThemeSelect testId="auth-login-theme-select" id="auth-login-theme" />
              </div>
            </div>
            <h1
              data-testid="auth-login-heading"
              className="mt-4 md:mt-6"
            >
              Iniciar sesión
            </h1>

            {formError ? (
              <div className="mt-3">
                <Alert
                  ref={formAlertRef}
                  testId="auth-login-form-alert"
                  tabIndex={-1}
                >
                  {formError}
                </Alert>
              </div>
            ) : null}

            {showExpiredNotice ? (
              <div className="mt-3">
                <Alert testId="auth-login-expired-alert">
                  Tu sesión expiró. Inicia sesión de nuevo.
                </Alert>
              </div>
            ) : null}

            <form
              data-testid="auth-login-form"
              noValidate
              onSubmit={handleSubmit}
              className="mt-6 flex flex-col gap-4"
            >
              <Input
                ref={emailRef}
                id="auth-login-email"
                testId="auth-login-email-input"
                label="Email"
                type="email"
                autoComplete="username"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                error={fieldErrors.email}
              />
              <Input
                ref={passwordRef}
                id="auth-login-password"
                testId="auth-login-password-input"
                label="Contraseña"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                error={fieldErrors.password}
              />
              <Button
                testId="auth-login-submit-button"
                type="submit"
                loading={isSubmitting}
                className="w-full"
              >
                {isSubmitting ? "Ingresando…" : "Ingresar"}
              </Button>
            </form>

            <section
              aria-labelledby="auth-login-demo-title"
              className="mt-8 rounded-lg border border-line bg-surface p-5"
            >
              <p
                id="auth-login-demo-title"
                data-testid="auth-login-demo-title-text"
                className="text-[13px] font-semibold"
              >
                Usuarios de demostración
              </p>
              <ul
                data-testid="auth-login-demo-list"
                className="mt-2 divide-y divide-line"
              >
                {DEMO_USERS.map((user) => (
                  <li
                    key={user.email}
                    data-testid={user.testId}
                    className="flex items-baseline justify-between gap-3 py-1.5"
                  >
                    <span className="text-ink">{user.email}</span>
                    <span className="text-[13px] text-muted">
                      {roleLabel(user.role)}
                    </span>
                  </li>
                ))}
              </ul>
              <p
                data-testid="auth-login-demo-password-text"
                className="mt-3 text-[13px] text-muted"
              >
                {DEMO_PASSWORD_TEXT}
              </p>
            </section>

            {/*
             * The targets of these two anchors are served by the API on
             * the same origin (the `/api` rewrite of next.config.ts), not
             * by Next.js routes: a client-side navigation would 404, so
             * they are plain anchors (full page load) and not `Link`,
             * which wraps the router. The link styling is the `text`
             * variant of the theme's Link.
             */}
            <p
              data-testid="auth-login-api-text"
              className="mt-3 text-[13px] text-muted"
            >
              Para probar la API:{" "}
              <a
                href="/api/docs"
                data-testid="auth-login-api-docs-link"
                className="text-accent underline underline-offset-2 hover:decoration-2 transition-colors duration-120"
              >
                Documentación interactiva
              </a>{" "}
              ·{" "}
              <a
                href="/api/openapi.json"
                data-testid="auth-login-api-contract-link"
                className="text-accent underline underline-offset-2 hover:decoration-2 transition-colors duration-120"
              >
                Contrato OpenAPI
              </a>
            </p>
          </div>
        </div>
      </main>
    </>
  );
}
