// US equity market session status (NYSE/Nasdaq regular hours, America/New_York).

export type SessionState = "pre_market" | "open" | "after_hours" | "closed" | "weekend" | "holiday";

// Published NYSE holiday schedule. Extend yearly; unknown years fall back to weekday rules only.
export const NYSE_HOLIDAYS: Record<string, string> = {
  "2026-01-01": "New Year's Day",
  "2026-01-19": "Martin Luther King Jr. Day",
  "2026-02-16": "Washington's Birthday",
  "2026-04-03": "Good Friday",
  "2026-05-25": "Memorial Day",
  "2026-06-19": "Juneteenth",
  "2026-07-03": "Independence Day (observed)",
  "2026-09-07": "Labor Day",
  "2026-11-26": "Thanksgiving Day",
  "2026-12-25": "Christmas Day",
};
export const NYSE_EARLY_CLOSES: Record<string, string> = {
  "2026-11-27": "13:00",
  "2026-12-24": "13:00",
};

export interface SessionInfo {
  state: SessionState;
  nyDate: string;
  nyTime: string; // HH:MM
  earlyClose: boolean;
  holidayName?: string | undefined;
}

function nyParts(now: Date) {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    weekday: "short",
    hourCycle: "h23",
  }).formatToParts(now);
  const get = (t: string) => parts.find((p) => p.type === t)?.value ?? "";
  return {
    date: `${get("year")}-${get("month")}-${get("day")}`,
    hour: Number(get("hour")),
    minute: Number(get("minute")),
    weekday: get("weekday"),
  };
}

export function getMarketSession(now: Date): SessionInfo {
  const p = nyParts(now);
  const nyTime = `${String(p.hour).padStart(2, "0")}:${String(p.minute).padStart(2, "0")}`;
  const base = { nyDate: p.date, nyTime, earlyClose: false };
  if (p.weekday === "Sat" || p.weekday === "Sun") return { ...base, state: "weekend" };
  if (NYSE_HOLIDAYS[p.date]) return { ...base, state: "holiday", holidayName: NYSE_HOLIDAYS[p.date] };

  const mins = p.hour * 60 + p.minute;
  const early = NYSE_EARLY_CLOSES[p.date];
  const closeMins = early ? Number(early.slice(0, 2)) * 60 + Number(early.slice(3)) : 16 * 60;
  const info = { ...base, earlyClose: Boolean(early) };
  if (mins >= 4 * 60 && mins < 9 * 60 + 30) return { ...info, state: "pre_market" };
  if (mins >= 9 * 60 + 30 && mins < closeMins) return { ...info, state: "open" };
  if (mins >= closeMins && mins < 20 * 60) return { ...info, state: "after_hours" };
  return { ...info, state: "closed" };
}

/** Business days (Mon–Fri) between an observation date and now; used for stale-data warnings. */
export function businessDaysSince(isoDate: string, now: Date): number {
  const start = new Date(isoDate + "T00:00:00Z");
  const end = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
  let days = 0;
  const d = new Date(start);
  while (d < end) {
    d.setUTCDate(d.getUTCDate() + 1);
    const wd = d.getUTCDay();
    if (wd !== 0 && wd !== 6) days++;
  }
  return days;
}

/** Daily series older than 3 business days are flagged stale. */
export function isStale(isoDate: string | null, now: Date, thresholdBusinessDays = 3): boolean {
  if (!isoDate) return false;
  return businessDaysSince(isoDate, now) > thresholdBusinessDays;
}
