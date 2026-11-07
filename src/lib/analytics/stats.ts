import { macd, rsi, sma } from "./indicators";

export interface ClosePoint {
  date: string;
  close: number;
}

export interface DescriptiveStats {
  mode: "price" | "level";
  observations: number;
  start: string;
  end: string;
  startValue: number;
  endValue: number;
  high: number;
  highDate: string;
  low: number;
  lowDate: string;
  /** price: % total return; level: absolute change */
  totalChange: number;
  cagrPct: number | null;
  /** price: annualized % vol of log returns; level: stdev of daily changes */
  dailyVol: number | null;
  maxDrawdownPct: number | null;
  maxDrawdownPeakDate: string | null;
  maxDrawdownTroughDate: string | null;
  bestDay: { date: string; value: number } | null;
  worstDay: { date: string; value: number } | null;
  upDaysPct: number | null;
}

export function describeSeries(points: ClosePoint[], mode: "price" | "level"): DescriptiveStats | null {
  if (points.length < 2) return null;
  const first = points[0];
  const last = points[points.length - 1];
  let high = first;
  let low = first;
  let peak = first;
  let maxDd = 0;
  let ddPeak: string | null = null;
  let ddTrough: string | null = null;
  const changes: { date: string; value: number }[] = [];

  for (let i = 0; i < points.length; i++) {
    const p = points[i];
    if (p.close > high.close) high = p;
    if (p.close < low.close) low = p;
    if (i > 0) {
      const prev = points[i - 1].close;
      changes.push({
        date: p.date,
        value: mode === "price" ? (p.close / prev - 1) * 100 : p.close - prev,
      });
    }
    if (mode === "price") {
      if (p.close > peak.close) peak = p;
      const dd = (p.close / peak.close - 1) * 100;
      if (dd < maxDd) {
        maxDd = dd;
        ddPeak = peak.date;
        ddTrough = p.date;
      }
    }
  }

  const years =
    (Date.parse(last.date + "T00:00:00Z") - Date.parse(first.date + "T00:00:00Z")) /
    (365.25 * 86400000);

  let dailyVol: number | null = null;
  if (changes.length > 2) {
    const vals =
      mode === "price"
        ? points.slice(1).map((p, i) => Math.log(p.close / points[i].close))
        : changes.map((c) => c.value);
    const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
    const sd = Math.sqrt(vals.reduce((a, b) => a + (b - mean) ** 2, 0) / (vals.length - 1));
    dailyVol = mode === "price" ? sd * Math.sqrt(252) * 100 : sd;
  }

  const sorted = [...changes].sort((a, b) => a.value - b.value);
  return {
    mode,
    observations: points.length,
    start: first.date,
    end: last.date,
    startValue: first.close,
    endValue: last.close,
    high: high.close,
    highDate: high.date,
    low: low.close,
    lowDate: low.date,
    totalChange: mode === "price" ? (last.close / first.close - 1) * 100 : last.close - first.close,
    cagrPct:
      mode === "price" && years >= 1 ? (Math.pow(last.close / first.close, 1 / years) - 1) * 100 : null,
    dailyVol,
    maxDrawdownPct: mode === "price" ? maxDd : null,
    maxDrawdownPeakDate: ddPeak,
    maxDrawdownTroughDate: ddTrough,
    bestDay: sorted.length ? sorted[sorted.length - 1] : null,
    worstDay: sorted.length ? sorted[0] : null,
    upDaysPct: changes.length ? (changes.filter((c) => c.value > 0).length / changes.length) * 100 : null,
  };
}

export type SignalId = "cross_above_sma200" | "golden_cross" | "rsi_below_30" | "macd_bull_cross";
export const SIGNAL_IDS: SignalId[] = [
  "cross_above_sma200",
  "golden_cross",
  "rsi_below_30",
  "macd_bull_cross",
];

/** Indices where the signal *event* fires (a crossing, not a persistent state). */
export function signalEvents(closes: number[], signal: SignalId): number[] {
  const events: number[] = [];
  if (signal === "cross_above_sma200") {
    const s = sma(closes, 200);
    for (let i = 1; i < closes.length; i++) {
      if (s[i] != null && s[i - 1] != null && closes[i - 1] <= s[i - 1]! && closes[i] > s[i]!)
        events.push(i);
    }
  } else if (signal === "golden_cross") {
    const s50 = sma(closes, 50);
    const s200 = sma(closes, 200);
    for (let i = 1; i < closes.length; i++) {
      if (
        s200[i] != null &&
        s200[i - 1] != null &&
        s50[i - 1]! <= s200[i - 1]! &&
        s50[i]! > s200[i]!
      )
        events.push(i);
    }
  } else if (signal === "rsi_below_30") {
    const r = rsi(closes, 14);
    for (let i = 1; i < closes.length; i++) {
      if (r[i] != null && r[i - 1] != null && r[i - 1]! >= 30 && r[i]! < 30) events.push(i);
    }
  } else if (signal === "macd_bull_cross") {
    const m = macd(closes);
    for (let i = 1; i < closes.length; i++) {
      const a0 = m.macd[i - 1];
      const b0 = m.signal[i - 1];
      const a1 = m.macd[i];
      const b1 = m.signal[i];
      if (a0 != null && b0 != null && a1 != null && b1 != null && a0 <= b0 && a1 > b1) events.push(i);
    }
  }
  return events;
}

export interface BucketStats {
  n: number;
  hitRatePct: number | null;
  avgFwdPct: number | null;
  medianFwdPct: number | null;
}

export interface SignalTestResult {
  signal: SignalId;
  horizon: number;
  events: BucketStats;
  baseline: BucketStats;
  /** Event average minus unconditional average, in percentage points. */
  excessAvgPct: number | null;
  inSample: BucketStats;
  outOfSample: BucketStats;
  splitDate: string | null;
  smallSample: boolean;
  lastEventDate: string | null;
}

function bucket(values: number[]): BucketStats {
  if (!values.length) return { n: 0, hitRatePct: null, avgFwdPct: null, medianFwdPct: null };
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return {
    n: values.length,
    hitRatePct: (values.filter((v) => v > 0).length / values.length) * 100,
    avgFwdPct: values.reduce((a, b) => a + b, 0) / values.length,
    medianFwdPct: sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2,
  };
}

/**
 * Event study: forward % return `horizon` bars after each signal event, compared with the
 * unconditional forward return of every eligible day in the same window. Descriptive only.
 * `fromIndex` excludes indicator warm-up bars from both events and baseline.
 */
export function testSignal(
  points: ClosePoint[],
  signal: SignalId,
  horizon: number,
  fromIndex = 0,
  splitRatio = 0.7,
): SignalTestResult {
  const closes = points.map((p) => p.close);
  const fwd = (i: number) => (closes[i + horizon] / closes[i] - 1) * 100;
  const lastEligible = closes.length - 1 - horizon;
  const events = signalEvents(closes, signal).filter((i) => i >= fromIndex && i <= lastEligible);

  const baseline: number[] = [];
  for (let i = fromIndex; i <= lastEligible; i++) baseline.push(fwd(i));

  const span = lastEligible - fromIndex;
  const splitIdx = span > 0 ? fromIndex + Math.floor(span * splitRatio) : fromIndex;
  const eventFwd = events.map(fwd);
  const ev = bucket(eventFwd);
  const base = bucket(baseline);

  return {
    signal,
    horizon,
    events: ev,
    baseline: base,
    excessAvgPct: ev.avgFwdPct != null && base.avgFwdPct != null ? ev.avgFwdPct - base.avgFwdPct : null,
    inSample: bucket(events.filter((i) => i < splitIdx).map(fwd)),
    outOfSample: bucket(events.filter((i) => i >= splitIdx).map(fwd)),
    splitDate: points[splitIdx]?.date ?? null,
    smallSample: ev.n < 30,
    lastEventDate: events.length ? points[events[events.length - 1]].date : null,
  };
}
