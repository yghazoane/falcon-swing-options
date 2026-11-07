// Orchestration layer: maps instruments/indicators to provider adapters, applies fallbacks,
// and returns plain DTOs. Secrets arrive as arguments from server-function handlers only.
import { ALL_QUOTE_IDS, INSTRUMENTS, SECTOR_ETFS } from "./market/instruments";
import type {
  Bar,
  BreadthResult,
  FedTarget,
  InstrumentId,
  MacroIndicator,
  MacroResult,
  NewsItem,
  NewsResult,
  OverviewResult,
  ProviderStatus,
  ProviderStatusResult,
  Quote,
  SectorRow,
  SeriesResult,
  SourceInfo,
  FeedStatus,
  MacroUnit,
} from "./market/types";
import { demoBars } from "./demo/demo-series";
import { failureNote } from "./providers/cache.server";
import {
  fetchFredCalendar,
  fetchFredSeries,
  fetchFredSeriesUpdated,
  fredSeriesUrl,
  type Observation,
} from "./providers/fred.server";
import { fetchPolygonDaily } from "./providers/polygon.server";
import { fetchFeed, fetchFinnhubNews, RSS_FEEDS } from "./providers/news.server";

export interface ProviderEnv {
  polygonKey?: string;
  fredKey?: string;
  finnhubKey?: string;
}

const FRED_NAME = "FRED · Federal Reserve Bank of St. Louis";

function isoDaysAgo(days: number, now = new Date()): string {
  const d = new Date(now.getTime() - days * 86400000);
  return d.toISOString().slice(0, 10);
}
const today = () => new Date().toISOString().slice(0, 10);

function demoSource(id: InstrumentId, note: string): SourceInfo {
  return { status: "demo", provider: "demo", providerName: "Demo / Illustrative", note };
}

/** Load bars for an instrument. `start` undefined = full available history. */
async function loadBars(
  id: InstrumentId,
  env: ProviderEnv,
  start?: string,
): Promise<{ bars: Bar[]; source: SourceInfo }> {
  const inst = INSTRUMENTS[id];
  if (inst.fred) {
    try {
      const obs = await fetchFredSeries(inst.fred, start);
      return {
        bars: obs.map((o) => ({ date: o.date, close: o.value })),
        source: {
          status: "eod",
          provider: "fred_public",
          providerName: FRED_NAME,
          sourceUrl: fredSeriesUrl(inst.fred),
        },
      };
    } catch (err) {
      console.error(`[fred] ${inst.fred} failed`, err);
      return {
        bars: [],
        source: {
          status: "error",
          provider: "fred_public",
          providerName: FRED_NAME,
          sourceUrl: fredSeriesUrl(inst.fred),
          note: failureNote(err),
        },
      };
    }
  }
  if (inst.polygon && env.polygonKey) {
    try {
      const bars = await fetchPolygonDaily(inst.polygon, start ?? isoDaysAgo(365 * 15), today(), env.polygonKey);
      return {
        bars,
        source: {
          status: "delayed",
          provider: "polygon",
          providerName: "Polygon.io / Massive",
          sourceUrl: `https://polygon.io/quote/${inst.polygon}`,
        },
      };
    } catch (err) {
      console.error(`[polygon] ${inst.polygon} failed`, err);
      return {
        bars: [],
        source: { status: "error", provider: "polygon", providerName: "Polygon.io / Massive", note: failureNote(err) },
      };
    }
  }
  // Not configured → clearly labeled demo series.
  const days = start ? Math.max(30, Math.ceil(((Date.now() - Date.parse(start)) / 86400000) * (5 / 7))) : 2600;
  const bars = demoBars(id, { ...inst.demo, days, end: new Date() });
  return { bars, source: demoSource(id, inst.polygon ? "polygon_not_configured" : "licensed_vendor_required") };
}

function toQuote(id: InstrumentId, bars: Bar[], source: SourceInfo): Quote {
  const last = bars[bars.length - 1];
  const prev = bars[bars.length - 2];
  const value = last?.close ?? null;
  const previous = prev?.close ?? null;
  return {
    id,
    ...source,
    value,
    previous,
    change: value != null && previous != null ? value - previous : null,
    changePct: value != null && previous ? (value / previous - 1) * 100 : null,
    asOf: last?.date ?? null,
    spark: bars.slice(-40).map((b) => b.close),
  };
}

export async function getOverviewData(env: ProviderEnv): Promise<OverviewResult> {
  const start = isoDaysAgo(90);
  const entries = await Promise.all(
    ALL_QUOTE_IDS.map(async (id) => {
      const { bars, source } = await loadBars(id, env, start);
      return [id, toQuote(id, bars, source)] as const;
    }),
  );
  return {
    generatedAt: new Date().toISOString(),
    quotes: Object.fromEntries(entries) as Record<InstrumentId, Quote>,
  };
}

export async function getSeriesData(
  id: InstrumentId,
  env: ProviderEnv,
  from?: string,
  to?: string,
): Promise<SeriesResult> {
  const { bars: all, source } = await loadBars(id, env);
  const inst = INSTRUMENTS[id];
  const bounded = to ? all.filter((b) => b.date <= to) : all;
  let idx = from ? bounded.findIndex((b) => b.date >= from) : 0;
  if (idx < 0) idx = bounded.length;
  const warm = Math.max(0, idx - 260);
  const bars = bounded.slice(warm);
  return {
    id,
    ...source,
    bars,
    hasVolume: bars.some((b) => b.volume != null),
    hasOHLC: bars.some((b) => b.open != null),
    asOf: all[all.length - 1]?.date ?? null,
    displayFrom: bounded[idx]?.date ?? null,
    note: source.note ?? (inst.licenseNote ? "licensed_vendor_required" : undefined),
  };
}

// ---------------- Macro ----------------

type Transform = "yoy_mom" | "diff" | "level" | "mom";
const MACRO_DEFS: { id: string; series: string | null; transform: Transform; unit: MacroUnit }[] = [
  { id: "cpi", series: "CPIAUCSL", transform: "yoy_mom", unit: "pct" },
  { id: "core_cpi", series: "CPILFESL", transform: "yoy_mom", unit: "pct" },
  { id: "pce", series: "PCEPI", transform: "yoy_mom", unit: "pct" },
  { id: "core_pce", series: "PCEPILFE", transform: "yoy_mom", unit: "pct" },
  { id: "ppi", series: "PPIFIS", transform: "yoy_mom", unit: "pct" },
  { id: "nfp", series: "PAYEMS", transform: "diff", unit: "thousands" },
  { id: "unemployment", series: "UNRATE", transform: "level", unit: "pct" },
  { id: "gdp", series: "A191RL1Q225SBEA", transform: "level", unit: "pct_saar" },
  { id: "retail_sales", series: "RSAFS", transform: "mom", unit: "pct" },
  { id: "ism_mfg", series: null, transform: "level", unit: "pct" },
];

export function transformMacro(obs: Observation[], t: Transform) {
  const n = obs.length;
  const pct = (a?: Observation, b?: Observation) => (a && b && b.value ? (a.value / b.value - 1) * 100 : null);
  const at = (k: number) => obs[n - 1 - k];
  switch (t) {
    case "yoy_mom":
      return {
        actual: pct(at(0), at(12)),
        previous: pct(at(1), at(13)),
        secondary: pct(at(0), at(1)),
        secondaryPrevious: pct(at(1), at(2)),
      };
    case "diff":
      return {
        actual: at(0) && at(1) ? at(0)!.value - at(1)!.value : null,
        previous: at(1) && at(2) ? at(1)!.value - at(2)!.value : null,
        secondary: null,
        secondaryPrevious: null,
      };
    case "mom":
      return { actual: pct(at(0), at(1)), previous: pct(at(1), at(2)), secondary: null, secondaryPrevious: null };
    default:
      return { actual: at(0)?.value ?? null, previous: at(1)?.value ?? null, secondary: null, secondaryPrevious: null };
  }
}

async function loadMacroIndicator(def: (typeof MACRO_DEFS)[number], env: ProviderEnv): Promise<MacroIndicator> {
  const empty = {
    id: def.id,
    series: def.series,
    actual: null,
    previous: null,
    forecast: null,
    secondary: null,
    secondaryPrevious: null,
    unit: def.unit,
    period: null,
    lastUpdatedAtSource: null,
  };
  if (!def.series) {
    return { ...empty, status: "unavailable", provider: "none", providerName: "—", note: "licensed_vendor_required" };
  }
  try {
    const obs = await fetchFredSeries(def.series, isoDaysAgo(365 * 3));
    let lastUpdated: string | null = null;
    if (env.fredKey) {
      lastUpdated = await fetchFredSeriesUpdated(def.series, env.fredKey).catch(() => null);
    }
    return {
      ...empty,
      ...transformMacro(obs, def.transform),
      period: obs[obs.length - 1]?.date ?? null,
      lastUpdatedAtSource: lastUpdated,
      status: "eod",
      provider: "fred_public",
      providerName: FRED_NAME,
      sourceUrl: fredSeriesUrl(def.series),
    };
  } catch (err) {
    console.error(`[macro] ${def.series} failed`, err);
    return {
      ...empty,
      status: "error",
      provider: "fred_public",
      providerName: FRED_NAME,
      sourceUrl: fredSeriesUrl(def.series),
      note: failureNote(err),
    };
  }
}

async function loadFedTarget(): Promise<FedTarget> {
  try {
    const [upper, lower] = await Promise.all([
      fetchFredSeries("DFEDTARU", "2008-12-16"),
      fetchFredSeries("DFEDTARL", "2008-12-16"),
    ]);
    const lastU = upper[upper.length - 1];
    const lastL = lower[lower.length - 1];
    let lastChangeDate: string | null = null;
    for (let i = upper.length - 1; i > 0; i--) {
      if (upper[i]!.value !== upper[i - 1]!.value) {
        lastChangeDate = upper[i]!.date;
        break;
      }
    }
    return {
      status: "eod",
      provider: "fred_public",
      providerName: FRED_NAME,
      sourceUrl: fredSeriesUrl("DFEDTARU"),
      upper: lastU?.value ?? null,
      lower: lastL?.value ?? null,
      asOf: lastU?.date ?? null,
      lastChangeDate,
    };
  } catch (err) {
    return {
      status: "error",
      provider: "fred_public",
      providerName: FRED_NAME,
      note: failureNote(err),
      upper: null,
      lower: null,
      asOf: null,
      lastChangeDate: null,
    };
  }
}

export async function getMacroData(env: ProviderEnv): Promise<MacroResult> {
  const fedFeed = RSS_FEEDS.find((f) => f.id === "fed_monetary")!;
  const [indicators, fedTarget, fomc, calendar] = await Promise.all([
    Promise.all(MACRO_DEFS.map((d) => loadMacroIndicator(d, env))),
    loadFedTarget(),
    fetchFeed(fedFeed).then(
      (items) => ({ status: "delayed" as const, items: items.slice(0, 8) }),
      () => ({ status: "error" as const, items: [] as NewsItem[] }),
    ),
    env.fredKey
      ? fetchFredCalendar(env.fredKey, today(), isoDaysAgo(-45)).then(
          (events) => ({ status: "eod" as const, events }),
          (err) => ({ status: "error" as const, note: failureNote(err), events: [] }),
        )
      : Promise.resolve({ status: "unavailable" as const, note: "fred_api_key_missing", events: [] }),
  ]);
  return {
    generatedAt: new Date().toISOString(),
    indicators,
    fedTarget,
    fomcCommunications: fomc.items,
    fomcStatus: fomc.status,
    calendar,
  };
}

// ---------------- News ----------------

export async function getNewsData(env: ProviderEnv): Promise<NewsResult> {
  const results = await Promise.allSettled(RSS_FEEDS.map((f) => fetchFeed(f)));
  const feeds: FeedStatus[] = RSS_FEEDS.map((f, i) => {
    const r = results[i]!;
    return r.status === "fulfilled"
      ? { id: f.id, name: f.name, status: "delayed", count: r.value.length, url: f.homepage }
      : { id: f.id, name: f.name, status: "error", count: 0, note: failureNote(r.reason), url: f.homepage };
  });
  const items: NewsItem[] = results.flatMap((r) => (r.status === "fulfilled" ? r.value : []));

  if (env.finnhubKey) {
    try {
      const fh = await fetchFinnhubNews(env.finnhubKey);
      items.push(...fh);
      feeds.push({ id: "finnhub", name: "Finnhub — Market News", status: "delayed", count: fh.length, url: "https://finnhub.io" });
    } catch (err) {
      feeds.push({ id: "finnhub", name: "Finnhub — Market News", status: "error", count: 0, note: failureNote(err), url: "https://finnhub.io" });
    }
  } else {
    feeds.push({ id: "finnhub", name: "Finnhub — Market News", status: "unavailable", count: 0, note: "not_configured", url: "https://finnhub.io" });
  }

  const seen = new Set<string>();
  const deduped = items.filter((it) => {
    if (seen.has(it.url)) return false;
    seen.add(it.url);
    return true;
  });
  deduped.sort((a, b) => (b.publishedAt ?? "").localeCompare(a.publishedAt ?? ""));
  return { generatedAt: new Date().toISOString(), items: deduped.slice(0, 80), feeds };
}

// ---------------- Breadth & sectors ----------------

export async function getBreadthData(env: ProviderEnv): Promise<BreadthResult> {
  const breadth: SourceInfo = {
    status: "unavailable",
    provider: "none",
    providerName: "—",
    note: "breadth_vendor_required",
  };
  if (!env.polygonKey) {
    return {
      generatedAt: new Date().toISOString(),
      breadth,
      sectors: { status: "unavailable", provider: "polygon", providerName: "Polygon.io / Massive", note: "polygon_not_configured", rows: [] },
    };
  }
  const key = env.polygonKey;
  const settled = await Promise.allSettled(
    SECTOR_ETFS.map((s) => fetchPolygonDaily(s.ticker, isoDaysAgo(50), today(), key)),
  );
  const rows: SectorRow[] = SECTOR_ETFS.map((s, i) => {
    const r = settled[i]!;
    if (r.status !== "fulfilled") return { ticker: s.ticker, sector: s.sector.en, last: null, d1: null, d5: null, m1: null, asOf: null };
    const b = r.value;
    const n = b.length;
    const ch = (k: number) => (n > k ? (b[n - 1]!.close / b[n - 1 - k]!.close - 1) * 100 : null);
    return { ticker: s.ticker, sector: s.sector.en, last: b[n - 1]?.close ?? null, d1: ch(1), d5: ch(5), m1: ch(21), asOf: b[n - 1]?.date ?? null };
  });
  const ok = settled.filter((s) => s.status === "fulfilled").length;
  return {
    generatedAt: new Date().toISOString(),
    breadth,
    sectors: {
      status: ok === 0 ? "error" : "delayed",
      provider: "polygon",
      providerName: "Polygon.io / Massive",
      note: ok === 0 ? failureNote((settled[0] as PromiseRejectedResult).reason) : ok < rows.length ? "partial" : undefined,
      rows,
    },
  };
}

// ---------------- Provider status ----------------

export async function getProviderStatusData(env: ProviderEnv): Promise<ProviderStatusResult> {
  const probe = async <T,>(fn: () => Promise<T>) => {
    try {
      return { ok: true as const, value: await fn() };
    } catch (err) {
      return { ok: false as const, note: failureNote(err) };
    }
  };

  const [fred, fredApi, polygon, finnhub, ...feeds] = await Promise.all([
    probe(() => fetchFredSeries("DGS10", isoDaysAgo(90))),
    env.fredKey ? probe(() => fetchFredSeriesUpdated("DGS10", env.fredKey!)) : Promise.resolve(null),
    env.polygonKey ? probe(() => fetchPolygonDaily("SPY", isoDaysAgo(90), today(), env.polygonKey!)) : Promise.resolve(null),
    env.finnhubKey ? probe(() => fetchFinnhubNews(env.finnhubKey!)) : Promise.resolve(null),
    ...RSS_FEEDS.map((f) => probe(() => fetchFeed(f))),
  ]);

  const providers: ProviderStatus[] = [
    {
      id: "fred_public",
      name: "FRED public data (St. Louis Fed)",
      category: "market",
      configured: true,
      requiresKey: false,
      envVars: [],
      implemented: true,
      status: fred.ok ? "eod" : "error",
      lastDataAt: fred.ok ? fred.value[fred.value.length - 1]?.date ?? null : null,
      note: fred.ok ? undefined : fred.note,
      url: "https://fred.stlouisfed.org",
      coverage: "fred_coverage",
    },
    {
      id: "fred_api",
      name: "FRED API",
      category: "macro",
      configured: Boolean(env.fredKey),
      requiresKey: true,
      envVars: ["FRED_API_KEY"],
      implemented: true,
      status: !fredApi ? "unavailable" : fredApi.ok ? "eod" : "error",
      lastDataAt: fredApi && fredApi.ok ? fredApi.value : null,
      note: !fredApi ? "not_configured" : fredApi.ok ? undefined : fredApi.note,
      url: "https://fred.stlouisfed.org/docs/api/api_key.html",
      coverage: "fred_api_coverage",
    },
    {
      id: "polygon",
      name: "Polygon.io / Massive",
      category: "market",
      configured: Boolean(env.polygonKey),
      requiresKey: true,
      envVars: ["POLYGON_API_KEY"],
      implemented: true,
      status: !polygon ? "demo" : polygon.ok ? "delayed" : "error",
      lastDataAt: polygon && polygon.ok ? polygon.value[polygon.value.length - 1]?.date ?? null : null,
      note: !polygon ? "not_configured_demo" : polygon.ok ? undefined : polygon.note,
      url: "https://polygon.io",
      coverage: "polygon_coverage",
    },
    {
      id: "finnhub",
      name: "Finnhub",
      category: "news",
      configured: Boolean(env.finnhubKey),
      requiresKey: true,
      envVars: ["FINNHUB_API_KEY"],
      implemented: true,
      status: !finnhub ? "unavailable" : finnhub.ok ? "delayed" : "error",
      lastDataAt: finnhub && finnhub.ok ? finnhub.value[0]?.publishedAt ?? null : null,
      note: !finnhub ? "not_configured" : finnhub.ok ? undefined : finnhub.note,
      url: "https://finnhub.io",
      coverage: "finnhub_coverage",
    },
    ...RSS_FEEDS.map((f, i): ProviderStatus => {
      const r = feeds[i]!;
      return {
        id: f.id,
        name: f.name,
        category: "news",
        configured: true,
        requiresKey: false,
        envVars: [],
        implemented: true,
        status: r.ok ? "delayed" : "error",
        lastDataAt: r.ok ? (r.value[0]?.publishedAt ?? null) : null,
        note: r.ok ? undefined : r.note,
        url: f.homepage,
        coverage: "rss_coverage",
      };
    }),
    {
      id: "breadth_vendor",
      name: "Market breadth vendor",
      category: "breadth",
      configured: false,
      requiresKey: true,
      envVars: ["BREADTH_PROVIDER", "BREADTH_API_KEY"],
      implemented: false,
      status: "unavailable",
      lastDataAt: null,
      note: "adapter_placeholder",
      url: "https://www.nyse.com/market-data",
      coverage: "breadth_coverage",
    },
    {
      id: "dxy_vendor",
      name: "ICE U.S. Dollar Index (DXY) vendor",
      category: "fx",
      configured: false,
      requiresKey: true,
      envVars: ["DXY_PROVIDER", "DXY_API_KEY"],
      implemented: false,
      status: "demo",
      lastDataAt: null,
      note: "adapter_placeholder",
      url: "https://www.ice.com/market-data",
      coverage: "dxy_coverage",
    },
    {
      id: "consensus_vendor",
      name: "Economic consensus forecasts",
      category: "consensus",
      configured: false,
      requiresKey: true,
      envVars: ["CONSENSUS_PROVIDER", "CONSENSUS_API_KEY"],
      implemented: false,
      status: "unavailable",
      lastDataAt: null,
      note: "adapter_placeholder",
      url: "https://fred.stlouisfed.org",
      coverage: "consensus_coverage",
    },
  ];
  return { generatedAt: new Date().toISOString(), providers };
}
