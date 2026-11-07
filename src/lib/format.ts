// Locale-aware, SSR-deterministic formatting. Numbers always use Latin digits (finance convention).
import type { Lang } from "./i18n/context";

const locale = (lang: Lang) => (lang === "ar" ? "ar-u-nu-latn" : "en-US");

export function fmtNum(v: number | null | undefined, decimals = 2): string {
  if (v == null || !Number.isFinite(v)) return "—";
  return v.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

export function fmtSigned(v: number | null | undefined, decimals = 2, suffix = ""): string {
  if (v == null || !Number.isFinite(v)) return "—";
  const s = fmtNum(Math.abs(v), decimals);
  return `${v > 0 ? "+" : v < 0 ? "−" : ""}${s}${suffix}`;
}

export function fmtCompact(v: number | null | undefined): string {
  if (v == null || !Number.isFinite(v)) return "—";
  return new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(v);
}

/** YYYY-MM-DD → localized date (UTC, so server and client agree). */
export function fmtDate(iso: string | null | undefined, lang: Lang, opts?: Intl.DateTimeFormatOptions): string {
  if (!iso) return "—";
  const d = new Date(iso.length === 10 ? iso + "T00:00:00Z" : iso);
  if (Number.isNaN(d.getTime())) return "—";
  return new Intl.DateTimeFormat(locale(lang), {
    year: "numeric",
    month: "short",
    day: "numeric",
    timeZone: "UTC",
    ...opts,
  }).format(d);
}

export function fmtMonth(iso: string | null | undefined, lang: Lang): string {
  return fmtDate(iso, lang, { day: undefined, month: "short", year: "numeric" });
}

/** ISO timestamp → New York time with ET suffix (deterministic across server/client). */
export function fmtDateTimeET(iso: string | null | undefined, lang: Lang): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  const s = new Intl.DateTimeFormat(locale(lang), {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "America/New_York",
  }).format(d);
  return `${s} ET`;
}
