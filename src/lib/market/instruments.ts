import type { InstrumentId, InstrumentKind } from "./types";

export interface InstrumentDef {
  id: InstrumentId;
  kind: InstrumentKind;
  symbol: string;
  name: { ar: string; en: string };
  /** For ETF proxies: the index this ETF tracks. The proxy is never the index itself. */
  proxyOf?: InstrumentId;
  fred?: string;
  polygon?: string;
  decimals: number;
  /** "price" instruments use % returns; "level" instruments (yields/spreads) use absolute changes. */
  mode: "price" | "level";
  unit?: "%" | "pp" | "$";
  demo: { base: number; vol: number; drift: number; volume?: number };
  licenseNote?: { ar: string; en: string };
}

export const INSTRUMENTS: Record<InstrumentId, InstrumentDef> = {
  SPX: {
    id: "SPX",
    kind: "index",
    symbol: "SPX",
    name: { ar: "مؤشر S&P 500", en: "S&P 500 Index" },
    fred: "SP500",
    decimals: 2,
    mode: "price",
    demo: { base: 5000, vol: 0.011, drift: 0.0003 },
  },
  NDX: {
    id: "NDX",
    kind: "index",
    symbol: "NDX",
    name: { ar: "مؤشر ناسداك 100", en: "Nasdaq-100 Index" },
    fred: "NASDAQ100",
    decimals: 2,
    mode: "price",
    demo: { base: 17000, vol: 0.014, drift: 0.0004 },
  },
  SPY: {
    id: "SPY",
    kind: "etf_proxy",
    symbol: "SPY",
    proxyOf: "SPX",
    name: { ar: "SPY — صندوق متداول يتتبع S&P 500", en: "SPY — ETF tracking the S&P 500" },
    polygon: "SPY",
    decimals: 2,
    mode: "price",
    demo: { base: 500, vol: 0.011, drift: 0.0003, volume: 75_000_000 },
  },
  QQQ: {
    id: "QQQ",
    kind: "etf_proxy",
    symbol: "QQQ",
    proxyOf: "NDX",
    name: { ar: "QQQ — صندوق متداول يتتبع ناسداك 100", en: "QQQ — ETF tracking the Nasdaq-100" },
    polygon: "QQQ",
    decimals: 2,
    mode: "price",
    demo: { base: 420, vol: 0.014, drift: 0.0004, volume: 45_000_000 },
  },
  VIX: {
    id: "VIX",
    kind: "volatility_index",
    symbol: "VIX",
    name: { ar: "مؤشر التقلب VIX", en: "Cboe Volatility Index (VIX)" },
    fred: "VIXCLS",
    decimals: 2,
    mode: "level",
    demo: { base: 16, vol: 0.06, drift: 0 },
  },
  US10Y: {
    id: "US10Y",
    kind: "rate",
    symbol: "US10Y",
    name: { ar: "عائد سندات الخزانة لأجل 10 سنوات", en: "US 10-Year Treasury Yield" },
    fred: "DGS10",
    decimals: 2,
    mode: "level",
    unit: "%",
    demo: { base: 4.2, vol: 0.012, drift: 0 },
  },
  US2Y: {
    id: "US2Y",
    kind: "rate",
    symbol: "US2Y",
    name: { ar: "عائد سندات الخزانة لأجل سنتين", en: "US 2-Year Treasury Yield" },
    fred: "DGS2",
    decimals: 2,
    mode: "level",
    unit: "%",
    demo: { base: 4.0, vol: 0.014, drift: 0 },
  },
  T10Y2Y: {
    id: "T10Y2Y",
    kind: "spread",
    symbol: "10Y–2Y",
    name: { ar: "فارق عائد 10 سنوات ناقص سنتين", en: "10Y minus 2Y Treasury spread" },
    fred: "T10Y2Y",
    decimals: 2,
    mode: "level",
    unit: "pp",
    demo: { base: 0.3, vol: 0.05, drift: 0 },
  },
  DXY: {
    id: "DXY",
    kind: "fx_index",
    symbol: "DXY",
    name: { ar: "مؤشر الدولار الأمريكي DXY", en: "US Dollar Index (DXY)" },
    decimals: 2,
    mode: "price",
    demo: { base: 100, vol: 0.004, drift: 0 },
    licenseNote: {
      ar: "مؤشر DXY مرخّص من ICE ويتطلب مزوّد بيانات مرخّصاً. القيمة المعروضة توضيحية فقط.",
      en: "DXY is licensed by ICE and requires a licensed vendor. The value shown is illustrative only.",
    },
  },
  USD_BROAD: {
    id: "USD_BROAD",
    kind: "fx_index",
    symbol: "USD Broad",
    name: {
      ar: "مؤشر الدولار الواسع (الاحتياطي الفيدرالي) — ليس DXY",
      en: "Fed Broad Dollar Index — not DXY",
    },
    fred: "DTWEXBGS",
    decimals: 2,
    mode: "price",
    demo: { base: 120, vol: 0.003, drift: 0 },
  },
  WTI: {
    id: "WTI",
    kind: "commodity",
    symbol: "WTI",
    name: { ar: "خام غرب تكساس الوسيط (WTI)", en: "WTI Crude Oil (spot)" },
    fred: "DCOILWTICO",
    decimals: 2,
    mode: "price",
    unit: "$",
    demo: { base: 75, vol: 0.02, drift: 0 },
  },
  BRENT: {
    id: "BRENT",
    kind: "commodity",
    symbol: "Brent",
    name: { ar: "خام برنت", en: "Brent Crude Oil (spot)" },
    fred: "DCOILBRENTEU",
    decimals: 2,
    mode: "price",
    unit: "$",
    demo: { base: 80, vol: 0.02, drift: 0 },
  },
  N225: {
    id: "N225",
    kind: "global_index",
    symbol: "N225",
    name: { ar: "مؤشر نيكاي 225 (اليابان)", en: "Nikkei 225 (Japan)" },
    fred: "NIKKEI225",
    decimals: 2,
    mode: "price",
    demo: { base: 38000, vol: 0.013, drift: 0.0003 },
  },
};

export const OVERVIEW_IDS: InstrumentId[] = ["SPX", "NDX", "VIX", "US10Y", "US2Y", "DXY"];
export const PROXY_IDS: InstrumentId[] = ["SPY", "QQQ"];
export const CONTEXT_IDS: InstrumentId[] = ["T10Y2Y", "USD_BROAD", "WTI", "BRENT", "N225"];
export const ALL_QUOTE_IDS: InstrumentId[] = [...OVERVIEW_IDS, ...PROXY_IDS, ...CONTEXT_IDS];
export const CHART_IDS: InstrumentId[] = ["SPX", "NDX", "SPY", "QQQ"];
export const HISTORY_IDS: InstrumentId[] = [
  "SPX",
  "NDX",
  "SPY",
  "QQQ",
  "VIX",
  "US10Y",
  "US2Y",
  "T10Y2Y",
  "WTI",
  "N225",
];

export function isInstrumentId(v: unknown): v is InstrumentId {
  return typeof v === "string" && v in INSTRUMENTS;
}

export const SECTOR_ETFS: { ticker: string; sector: { ar: string; en: string } }[] = [
  { ticker: "XLK", sector: { ar: "التكنولوجيا", en: "Technology" } },
  { ticker: "XLC", sector: { ar: "خدمات الاتصالات", en: "Communication Services" } },
  { ticker: "XLY", sector: { ar: "السلع الاستهلاكية الكمالية", en: "Consumer Discretionary" } },
  { ticker: "XLP", sector: { ar: "السلع الاستهلاكية الأساسية", en: "Consumer Staples" } },
  { ticker: "XLF", sector: { ar: "المالية", en: "Financials" } },
  { ticker: "XLV", sector: { ar: "الرعاية الصحية", en: "Health Care" } },
  { ticker: "XLI", sector: { ar: "الصناعات", en: "Industrials" } },
  { ticker: "XLE", sector: { ar: "الطاقة", en: "Energy" } },
  { ticker: "XLB", sector: { ar: "المواد", en: "Materials" } },
  { ticker: "XLU", sector: { ar: "المرافق", en: "Utilities" } },
  { ticker: "XLRE", sector: { ar: "العقارات", en: "Real Estate" } },
];
