"use client";

import { Button, Input } from "@/components/ui";
import { useLogin } from "@/features/auth/hooks";
import { DEMO_PASSWORD_TEXT, DEMO_USERS } from "@/features/auth/demo";
import { roleLabel } from "@/features/auth/types";
import { ApiRequestError, INTERNAL_ERROR_DETAIL } from "@/lib/api";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

const REQUIRED_MESSAGE = "Este campo es obligatorio.";

type LoginField = "email" | "password";

type LoginFieldErrors = Partial<Record<LoginField, string>>;

export default function LoginPage() {
  const router = useRouter();
  const login = useLogin();

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
    <div>
      <h1 data-testid="auth-login-heading">Iniciar sesión</h1>

      {formError ? (
        <p
          ref={formAlertRef}
          role="alert"
          data-testid="auth-login-form-alert"
          tabIndex={-1}
        >
          {formError}
        </p>
      ) : null}

      <form
        data-testid="auth-login-form"
        noValidate
        onSubmit={handleSubmit}
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
        >
          {isSubmitting ? "Ingresando…" : "Ingresar"}
        </Button>
      </form>

      <section aria-labelledby="auth-login-demo-title">
        <p id="auth-login-demo-title" data-testid="auth-login-demo-title-text">
          Usuarios de demostración
        </p>
        <ul data-testid="auth-login-demo-list">
          {DEMO_USERS.map((user) => (
            <li key={user.email} data-testid={user.testId}>
              {user.email} · {roleLabel(user.role)}
            </li>
          ))}
        </ul>
        <p data-testid="auth-login-demo-password-text">{DEMO_PASSWORD_TEXT}</p>
      </section>
    </div>
  );
}
