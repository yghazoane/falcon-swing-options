// Shared, client-safe data contracts for every provider adapter and server function.

/**
 * live        – real-time feed from a configured licensed provider
 * delayed     – provider data that may be delayed (depends on the user's plan)
 * eod         – end-of-day / latest published observation from an official source
 * demo        – generated illustrative values; never a real quote
 * unavailable – no provider configured for this data
 * error       – a configured provider failed
 */
export type DataStatus = "live" | "delayed" | "eod" | "demo" | "unavailable" | "error";

export type InstrumentKind =
  | "index"
  | "etf_proxy"
  | "volatility_index"
  | "rate"
  | "spread"
  | "fx_index"
  | "commodity"
  | "global_index";

export type InstrumentId =
  | "SPX"
  | "NDX"
  | "SPY"
  | "QQQ"
  | "VIX"
  | "US10Y"
  | "US2Y"
  | "T10Y2Y"
  | "DXY"
  | "USD_BROAD"
  | "WTI"
  | "BRENT"
  | "N225";

export interface Bar {
  date: string; // YYYY-MM-DD
  open?: number;
  high?: number;
  low?: number;
  close: number;
  volume?: number;
}

export interface SourceInfo {
  status: DataStatus;
  provider: string; // provider id, e.g. "fred_public"
  providerName: string;
  sourceUrl?: string;
  /** Short machine-safe reason, shown in UI when status is error/unavailable. */
  note?: string;
}

export interface Quote extends SourceInfo {
  id: InstrumentId;
  value: number | null;
  previous: number | null;
  change: number | null;
  changePct: number | null;
  asOf: string | null; // YYYY-MM-DD of latest observation
  spark: number[];
}

export interface SeriesResult extends SourceInfo {
  id: InstrumentId;
  bars: Bar[];
  hasVolume: boolean;
  hasOHLC: boolean;
  asOf: string | null;
  /** First date that should be displayed; earlier bars are indicator warm-up. */
  displayFrom: string | null;
}

export interface OverviewResult {
  generatedAt: string; // ISO timestamp
  quotes: Record<InstrumentId, Quote>;
}

export type MacroUnit = "pct" | "thousands" | "pct_saar";

export interface MacroIndicator extends SourceInfo {
  id: string;
  series: string | null;
  /** Primary transformed value (e.g. YoY %). */
  actual: number | null;
  previous: number | null;
  /** Consensus forecasts require a licensed provider — null unless sourced. */
  forecast: number | null;
  secondary: number | null; // e.g. MoM %
  secondaryPrevious: number | null;
  unit: MacroUnit;
  period: string | null; // observation period (YYYY-MM-DD)
  lastUpdatedAtSource: string | null; // from FRED API metadata when configured
}

export interface CalendarEvent {
  date: string;
  releaseName: string;
  releaseId: number;
  sourceUrl: string;
}

export interface FedTarget extends SourceInfo {
  lower: number | null;
  upper: number | null;
  asOf: string | null;
  lastChangeDate: string | null;
}

export type NewsCategory = "monetary_policy" | "economic_data" | "regulation" | "markets" | "banking";
export type NewsImportance = "high" | "medium" | "low";

export interface NewsItem {
  id: string;
  title: string;
  url: string;
  publisher: string;
  feedId: string;
  publishedAt: string | null; // ISO
  category: NewsCategory;
  importance: NewsImportance;
  excerpt: string | null;
}

export interface FeedStatus {
  id: string;
  name: string;
  status: DataStatus;
  count: number;
  note?: string;
  url: string;
}

export interface NewsResult {
  generatedAt: string;
  items: NewsItem[];
  feeds: FeedStatus[];
}

export interface MacroResult {
  generatedAt: string;
  indicators: MacroIndicator[];
  fedTarget: FedTarget;
  fomcCommunications: NewsItem[];
  fomcStatus: DataStatus;
  calendar: { status: DataStatus; note?: string; events: CalendarEvent[] };
}

export interface SectorRow {
  ticker: string;
  sector: string;
  last: number | null;
  d1: number | null;
  d5: number | null;
  m1: number | null;
  asOf: string | null;
}

export interface BreadthResult {
  generatedAt: string;
  breadth: SourceInfo;
  sectors: SourceInfo & { rows: SectorRow[] };
}

export interface ProviderStatus {
  id: string;
  name: string;
  category: "market" | "macro" | "news" | "breadth" | "fx" | "consensus";
  configured: boolean;
  requiresKey: boolean;
  envVars: string[];
  status: DataStatus;
  implemented: boolean;
  lastDataAt: string | null;
  note?: string;
  url: string;
  coverage: string;
}

export interface ProviderStatusResult {
  generatedAt: string;
  providers: ProviderStatus[];
}
