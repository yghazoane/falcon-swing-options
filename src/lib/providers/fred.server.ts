// FRED (Federal Reserve Bank of St. Louis) adapter.
// - Public CSV downloads: no key required, end-of-day / latest published observations.
// - FRED API (optional FRED_API_KEY): series metadata and the release calendar.
import { cached, fetchWithTimeout, ProviderError } from "./cache.server";
import type { CalendarEvent } from "../market/types";

export interface Observation {
  date: string;
  value: number;
}

export function parseFredCsv(csv: string): Observation[] {
  const lines = csv.trim().split(/\r?\n/);
  const header = lines[0]?.toLowerCase() ?? "";
  if (!header.startsWith("observation_date") && !header.startsWith("date")) {
    throw new ProviderError("fred_public", "parse", "Unexpected FRED CSV format");
  }
  const out: Observation[] = [];
  for (let i = 1; i < lines.length; i++) {
    const [date, raw] = lines[i].split(",");
    const value = Number(raw);
    if (!date || raw === undefined || raw === "." || raw === "" || !Number.isFinite(value)) continue;
    out.push({ date, value });
  }
  return out;
}

export function fredSeriesUrl(id: string) {
  return `https://fred.stlouisfed.org/series/${id}`;
}

/** Fetch a FRED series as CSV. `start` limits history (YYYY-MM-DD). Cached 30 minutes. */
export function fetchFredSeries(id: string, start?: string): Promise<Observation[]> {
  return cached(`fred:${id}:${start ?? "max"}`, 30 * 60 * 1000, async () => {
    const url =
      `https://fred.stlouisfed.org/graph/fredgraph.csv?id=${encodeURIComponent(id)}` +
      (start ? `&cosd=${start}` : "");
    const res = await fetchWithTimeout(url, {}, 12000);
    if (!res.ok) throw new ProviderError("fred_public", "http", `HTTP ${res.status}`);
    const data = parseFredCsv(await res.text());
    if (!data.length) throw new ProviderError("fred_public", "parse", "Empty series");
    return data;
  });
}

/** FRED API: when the series was last updated at the source. Requires FRED_API_KEY. */
export function fetchFredSeriesUpdated(id: string, apiKey: string): Promise<string | null> {
  return cached(`fredapi:series:${id}`, 6 * 60 * 60 * 1000, async () => {
    const url = `https://api.stlouisfed.org/fred/series?series_id=${encodeURIComponent(id)}&api_key=${apiKey}&file_type=json`;
    const res = await fetchWithTimeout(url);
    if (res.status === 400 || res.status === 401 || res.status === 403)
      throw new ProviderError("fred_api", "auth", "FRED API rejected the key");
    if (res.status === 429) throw new ProviderError("fred_api", "rate_limit", "Rate limited");
    if (!res.ok) throw new ProviderError("fred_api", "http", `HTTP ${res.status}`);
    const json = (await res.json()) as { seriess?: { last_updated?: string }[] };
    return json.seriess?.[0]?.last_updated ?? null;
  });
}

const CALENDAR_KEYWORDS = [
  "consumer price index",
  "employment situation",
  "personal income and outlays",
  "producer price index",
  "gross domestic product",
  "advance monthly sales",
  "job openings",
  "fomc",
  "h.15",
];

/** FRED API release calendar for the next `days` days, filtered to market-moving releases. */
export function fetchFredCalendar(apiKey: string, from: string, to: string): Promise<CalendarEvent[]> {
  return cached(`fredapi:calendar:${from}:${to}`, 6 * 60 * 60 * 1000, async () => {
    const url =
      `https://api.stlouisfed.org/fred/releases/dates?api_key=${apiKey}&file_type=json` +
      `&realtime_start=${from}&realtime_end=${to}&include_release_dates_with_no_data=true&sort_order=asc&limit=1000`;
    const res = await fetchWithTimeout(url);
    if (res.status === 400 || res.status === 401 || res.status === 403)
      throw new ProviderError("fred_api", "auth", "FRED API rejected the key");
    if (!res.ok) throw new ProviderError("fred_api", "http", `HTTP ${res.status}`);
    const json = (await res.json()) as {
      release_dates?: { release_id: number; release_name: string; date: string }[];
    };
    return (json.release_dates ?? [])
      .filter((r) => CALENDAR_KEYWORDS.some((k) => r.release_name.toLowerCase().includes(k)))
      .map((r) => ({
        date: r.date,
        releaseId: r.release_id,
        releaseName: r.release_name,
        sourceUrl: `https://fred.stlouisfed.org/release?rid=${r.release_id}`,
      }));
  });
}
