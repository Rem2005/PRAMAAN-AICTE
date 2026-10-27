/** Formatting helpers shared by administrative screens.
 *
 * The API returns naive UTC timestamps (no offset suffix), which JavaScript
 * would otherwise read as local time. `asUtc` normalises that before display.
 * Times are shown in IST and every surface that shows them says so.
 */

const IST_TIME_ZONE = "Asia/Kolkata";

function asUtc(value: string): Date | null {
  if (!value) return null;
  const hasZone = /(?:Z|[+-]\d{2}:?\d{2})$/.test(value);
  const parsed = new Date(hasZone ? value : `${value}Z`);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

export function formatDateIST(value: string): string {
  const date = asUtc(value);
  if (!date) return "—";
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: IST_TIME_ZONE,
  }).format(date);
}

export function formatTimeIST(value: string): string {
  const date = asUtc(value);
  if (!date) return "—";
  return new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: IST_TIME_ZONE,
  }).format(date);
}

/** e.g. "24 Oct 2026, 10:42" (IST). */
export function formatDateTimeIST(value: string): string {
  const date = asUtc(value);
  if (!date) return "—";
  return `${formatDateIST(value)}, ${formatTimeIST(value)}`;
}

export function formatCount(value: number): string {
  return value.toLocaleString("en-IN");
}
