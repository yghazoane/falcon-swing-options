// Polygon.io (now Massive) adapter for ETF proxies (SPY, QQQ, sector SPDRs).
// Requires POLYGON_API_KEY. Timeliness (real-time vs delayed vs EOD) depends on the user's plan.
import { cached, fetchWithTimeout, ProviderError } from "./cache.server";
import type { Bar } from "../market/types";

interface Agg {
  t: number;
  o: number;
  h: number;
  l: number;
  c: number;
  v: number;
}

export function fetchPolygonDaily(
  ticker: string,
  from: string,
  to: string,
  apiKey: string,
): Promise<Bar[]> {
  return cached(`polygon:${ticker}:${from}:${to}`, 15 * 60 * 1000, async () => {
    const url =
      `https://api.polygon.io/v2/aggs/ticker/${encodeURIComponent(ticker)}/range/1/day/${from}/${to}` +
      `?adjusted=true&sort=asc&limit=50000`;
    const res = await fetchWithTimeout(url, { headers: { Authorization: `Bearer ${apiKey}` } });
    if (res.status === 401 || res.status === 403)
      throw new ProviderError("polygon", "auth", "Polygon rejected the key or plan");
    if (res.status === 429) throw new ProviderError("polygon", "rate_limit", "Rate limited");
    if (!res.ok) throw new ProviderError("polygon", "http", `HTTP ${res.status}`);
    const json = (await res.json()) as { results?: Agg[] };
    const bars = (json.results ?? []).map((a) => ({
      date: new Date(a.t).toISOString().slice(0, 10),
      open: a.o,
      high: a.h,
      low: a.l,
      close: a.c,
      volume: a.v,
    }));
    if (!bars.length) throw new ProviderError("polygon", "parse", "No bars returned");
    return bars;
  });
}
