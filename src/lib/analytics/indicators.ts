// Pure technical-indicator math. Arrays are aligned with the input; warm-up slots are null.

export type Num = number | null;

export function sma(input: number[], period: number): Num[] {
  const out: Num[] = new Array(values.length).fill(null);
  if (period <= 0) return out;
  let sum = 0;
  for (let i = 0; i < values.length; i++) {
    sum += values[i];
    if (i >= period) sum -= values[i - period];
    if (i >= period - 1) out[i] = sum / period;
  }
  return out;
}

/** EMA seeded with the SMA of the first `period` values. */
export function ema(values: number[], period: number): Num[] {
  const out: Num[] = new Array(values.length).fill(null);
  if (values.length < period || period <= 0) return out;
  const k = 2 / (period + 1);
  let prev = 0;
  for (let i = 0; i < period; i++) prev += values[i];
  prev /= period;
  out[period - 1] = prev;
  for (let i = period; i < values.length; i++) {
    prev = values[i] * k + prev * (1 - k);
    out[i] = prev;
  }
  return out;
}

/** Wilder's RSI. */
export function rsi(values: number[], period = 14): Num[] {
  const out: Num[] = new Array(values.length).fill(null);
  if (values.length <= period) return out;
  let gain = 0;
  let loss = 0;
  for (let i = 1; i <= period; i++) {
    const d = values[i] - values[i - 1];
    if (d >= 0) gain += d;
    else loss -= d;
  }
  let avgGain = gain / period;
  let avgLoss = loss / period;
  out[period] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);
  for (let i = period + 1; i < values.length; i++) {
    const d = values[i] - values[i - 1];
    avgGain = (avgGain * (period - 1) + Math.max(d, 0)) / period;
    avgLoss = (avgLoss * (period - 1) + Math.max(-d, 0)) / period;
    out[i] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);
  }
  return out;
}

export function macd(
  values: number[],
  fast = 12,
  slow = 26,
  signalPeriod = 9,
): { macd: Num[]; signal: Num[]; hist: Num[] } {
  const f = ema(values, fast);
  const s = ema(values, slow);
  const line: Num[] = values.map((_, i) => (f[i] != null && s[i] != null ? f[i]! - s[i]! : null));
  const firstIdx = line.findIndex((v) => v != null);
  const signal: Num[] = new Array(values.length).fill(null);
  if (firstIdx >= 0) {
    const compact = line.slice(firstIdx) as number[];
    const sig = ema(compact, signalPeriod);
    sig.forEach((v, j) => (signal[firstIdx + j] = v));
  }
  const hist: Num[] = line.map((v, i) => (v != null && signal[i] != null ? v - signal[i]! : null));
  return { macd: line, signal, hist };
}

/**
 * Rolling realized volatility, in percent.
 * mode "price": stdev of log returns × √252 × 100 (annualized).
 * mode "level": stdev of daily absolute changes (same units as input), not annualized.
 */
export function rollingVolatility(
  values: number[],
  window = 20,
  mode: "price" | "level" = "price",
): Num[] {
  const out: Num[] = new Array(values.length).fill(null);
  const rets: number[] = [];
  for (let i = 1; i < values.length; i++) {
    rets.push(
      mode === "price" ? Math.log(values[i] / values[i - 1]) : values[i] - values[i - 1],
    );
  }
  for (let i = window; i < values.length; i++) {
    const slice = rets.slice(i - window, i);
    const mean = slice.reduce((a, b) => a + b, 0) / window;
    const variance = slice.reduce((a, b) => a + (b - mean) ** 2, 0) / (window - 1);
    const sd = Math.sqrt(variance);
    out[i] = mode === "price" ? sd * Math.sqrt(252) * 100 : sd;
  }
  return out;
}
