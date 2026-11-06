/**
 * Shared formatting of the "Libro mayor" front end, following
 * docs/SPEC.md section 8: USD money as `$1,234.50` and UTC dates and
 * times, never converted to the viewer's time zone.
 */

const MONEY_FORMAT = new Intl.NumberFormat("es-US", {
  style: "currency",
  currency: "USD",
});

const DATE_FORMAT = new Intl.DateTimeFormat("es-US", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  timeZone: "UTC",
});

const TIME_FORMAT = new Intl.DateTimeFormat("es-US", {
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
  timeZone: "UTC",
});

/**
 * Formats the money of the API (`"19.90"`, 2 decimals as a string) as
 * `$19.90`. The string goes through `Number` only for the formatter; the
 * value itself is never rounded on the client.
 */
export function formatMoney(value: string): string {
  return MONEY_FORMAT.format(Number(value));
}

/**
 * Formats one timestamp as `31/10/2026` in UTC. The `2-digit` options are
 * what make `es-US` zero-pad; without them `3/1/2026` would slip into the
 * UI. An invalid timestamp is returned unchanged instead of showing the
 * browser's "Invalid Date".
 */
export function formatDate(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return DATE_FORMAT.format(date);
}

/** Formats the time of one timestamp as `02:30` in UTC (23-hour cycle). */
export function formatTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return TIME_FORMAT.format(date);
}

/** Formats `31/10/2026 02:30 UTC`: date and time plus the UTC suffix. */
export function formatDateTime(iso: string): string {
  return `${formatDate(iso)} ${formatTime(iso)} UTC`;
}
