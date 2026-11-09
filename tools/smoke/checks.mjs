// Pure helpers of the online smoke test (task 069). No network, no files: the
// command in online-smoke.mjs asks these functions whether an answer is right,
// and the tests of checks.test.mjs call them with hand-written answers.

/** The session cookie of the API (SPEC section 3). */
export const SESSION_COOKIE = "labapp_session";

function headerValue(headers, name) {
  if (headers && typeof headers.get === "function") {
    return headers.get(name);
  }
  const key = Object.keys(headers ?? {}).find(
    (candidate) => candidate.toLowerCase() === name.toLowerCase(),
  );
  return key === undefined ? null : headers[key];
}

/**
 * The failures of a set of header expectations.
 *
 * `headers` is a `Headers` instance or a plain object (the lookup ignores the
 * case). Each expectation is one of:
 *   - `{ name, equals }`: the header must be present with exactly this value;
 *   - `{ name, matches }`: the header must be present and match the RegExp;
 *   - `{ name, absent: true }`: the header must not be sent.
 * Returns one message per failing expectation, with the expected and the
 * actual value; an empty array means every expectation holds.
 */
export function headerFailures(headers, expectations) {
  const failures = [];
  for (const expectation of expectations) {
    const value = headerValue(headers, expectation.name);
    if (expectation.absent) {
      if (value !== null) {
        failures.push(
          `header "${expectation.name}" was "${value}", expected no header`,
        );
      }
      continue;
    }
    if (value === null) {
      const expected =
        expectation.equals !== undefined
          ? `"${expectation.equals}"`
          : expectation.matches;
      failures.push(
        `header "${expectation.name}" is missing, expected ${expected}`,
      );
      continue;
    }
    if (expectation.equals !== undefined && value !== expectation.equals) {
      failures.push(
        `header "${expectation.name}" was "${value}", expected "${expectation.equals}"`,
      );
    }
    if (expectation.matches !== undefined && !expectation.matches.test(value)) {
      failures.push(
        `header "${expectation.name}" was "${value}", expected a value matching ${expectation.matches}`,
      );
    }
  }
  return failures;
}

/**
 * The value and the failures of the session cookie of a login answer.
 *
 * `setCookies` is the result of `response.headers.getSetCookie()` (or one
 * string). `secure` is whether the base of the check is https. The cookie must
 * be `HttpOnly`, carry `SameSite=Lax` (SPEC section 3) and carry `Secure` when
 * the base is https, and must not carry it on a plain http base.
 */
export function sessionCookie(setCookies, { secure = false } = {}) {
  const cookies = [].concat(setCookies ?? []);
  const raw = cookies.find(
    (cookie) =>
      typeof cookie === "string" &&
      cookie.trim().toLowerCase().startsWith(`${SESSION_COOKIE}=`),
  );
  if (!raw) {
    return {
      value: null,
      failures: [`the answer sets no ${SESSION_COOKIE} cookie`],
    };
  }

  const parts = raw.split(";").map((part) => part.trim());
  const pair = parts.shift() ?? "";
  const value = pair.slice(SESSION_COOKIE.length + 1);
  const attributes = new Map();
  for (const part of parts) {
    const separator = part.indexOf("=");
    if (separator === -1) {
      attributes.set(part.toLowerCase(), "");
    } else {
      attributes.set(
        part.slice(0, separator).toLowerCase(),
        part.slice(separator + 1),
      );
    }
  }

  const failures = [];
  if (!value) {
    failures.push(`the ${SESSION_COOKIE} cookie has an empty value`);
  }
  if (!attributes.has("httponly")) {
    failures.push(`the ${SESSION_COOKIE} cookie is not HttpOnly`);
  }
  const sameSite = attributes.get("samesite");
  if (sameSite === undefined) {
    failures.push(`the ${SESSION_COOKIE} cookie has no SameSite attribute`);
  } else if (sameSite.toLowerCase() !== "lax") {
    failures.push(
      `the ${SESSION_COOKIE} cookie has SameSite=${sameSite}, expected SameSite=Lax`,
    );
  }
  const isSecure = attributes.has("secure");
  if (secure && !isSecure) {
    failures.push(
      `the ${SESSION_COOKIE} cookie is not Secure on an https deployment`,
    );
  }
  if (!secure && isSecure) {
    failures.push(
      `the ${SESSION_COOKIE} cookie is Secure on a plain http base`,
    );
  }
  return { value, failures };
}

/**
 * The failures of an `application/problem+json` answer (SPEC section 8). The
 * body is the text of the answer; `status` and `code` are what the check
 * expects. The document must be an object with a string `type`, `title` and
 * `detail`, the expected `status` and the expected stable `code`.
 */
export function problemFailures(body, { contentType = "", status, code } = {}) {
  const failures = [];
  if (!String(contentType).toLowerCase().startsWith("application/problem+json")) {
    failures.push(
      `the answer is "${contentType || "(no content type)"}", expected application/problem+json`,
    );
  }
  let document;
  try {
    document = JSON.parse(body);
  } catch {
    failures.push("the body is not JSON");
    return failures;
  }
  if (
    document === null ||
    typeof document !== "object" ||
    Array.isArray(document)
  ) {
    failures.push("the problem document is not a JSON object");
    return failures;
  }
  if (typeof document.type !== "string") {
    failures.push("the problem document has no type");
  }
  if (typeof document.title !== "string") {
    failures.push("the problem document has no title");
  }
  if (typeof document.detail !== "string") {
    failures.push("the problem document has no detail");
  }
  if (status !== undefined && document.status !== status) {
    failures.push(
      `the problem document says status ${JSON.stringify(document.status)}, expected ${status}`,
    );
  }
  if (code !== undefined && document.code !== code) {
    failures.push(
      `the problem document says code ${JSON.stringify(document.code)}, expected "${code}"`,
    );
  }
  return failures;
}

/**
 * A fetch with the retry policy of the smoke test: up to `attempts` calls,
 * `delayMs` apart, until `accept` holds. The defaults are the health check
 * (five attempts, five seconds apart, a 200). `fetchImpl`, `sleep` and `clock`
 * are injected so the tests need no network and no real time.
 *
 * Returns `{ response, attempts, waitedMs }`, where `response` is the last
 * answer (accepted or not). A `fetchImpl` that throws is retried too; when the
 * last attempt throws, the error is rethrown.
 */
export async function retryingFetch(url, init = {}, options = {}) {
  const {
    attempts = 5,
    delayMs = 5000,
    fetchImpl = fetch,
    sleep = (milliseconds) =>
      new Promise((resolve) => setTimeout(resolve, milliseconds)),
    accept = (response) => response.status === 200,
    clock = () => Date.now(),
  } = options;

  const startedAt = clock();
  let lastError = null;
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try {
      const response = await fetchImpl(url, init);
      if (accept(response) || attempt === attempts) {
        return { response, attempts: attempt, waitedMs: clock() - startedAt };
      }
    } catch (error) {
      lastError = error;
      if (attempt === attempts) {
        throw error;
      }
    }
    await sleep(delayMs);
  }
  throw lastError ?? new Error("the retry policy made no attempt");
}

/**
 * The demo password, read from the sentence of docs/SEED.md that the login
 * screen displays. Returns `null` when the sentence is missing, so the command
 * can fail with a clear message instead of guessing a password.
 */
export function demoPassword(text) {
  const match = /demo password `([^`\n]+)`/i.exec(text);
  return match ? match[1] : null;
}

/** The first line of a CSV document, without its CRLF or LF end. */
export function firstCsvLine(text) {
  return String(text).split(/\r?\n/, 1)[0];
}
