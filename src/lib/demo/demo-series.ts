// Deterministic illustrative series. Output is ALWAYS labeled "Demo / Illustrative" in the UI
// and must never be presented as a real quote. Built lazily (no randomness at module scope).
import type { Bar } from "../market/types";

function hash(str: string): number {
  let h = 2166136261;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

export function seededRandom(seedKey: string) {
  let a = hash(seedKey);
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function gaussian(rand: () => number) {
  const u = Math.max(rand(), 1e-9);
  const v = rand();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}

/** Last weekday (UTC) on or before `now`. */
export function lastWeekday(now: Date): Date {
  const d = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
  while (d.getUTCDay() === 0 || d.getUTCDay() === 6) d.setUTCDate(d.getUTCDate() - 1);
  return d;
}

export function demoBars(
  seedKey: string,
  opts: { base: number; vol: number; drift: number; volume?: number; days: number; end: Date },
): Bar[] {
  const rand = seededRandom(`${seedKey}|${opts.days}`);
  const dates: string[] = [];
  const d = lastWeekday(opts.end);
  while (dates.length < opts.days) {
    if (d.getUTCDay() !== 0 && d.getUTCDay() !== 6) dates.push(d.toISOString().slice(0, 10));
    d.setUTCDate(d.getUTCDate() - 1);
  }
  dates.reverse();
  let price = opts.base;
  return dates.map((date) => {
    const open = price;
    const r = opts.drift + opts.vol * gaussian(rand);
    const close = Math.max(open * Math.exp(r), 0.01);
    const range = Math.abs(gaussian(rand)) * opts.vol * open * 0.6;
    price = close;
    return {
      date,
      open,
      close,
      high: Math.max(open, close) + range,
      low: Math.max(Math.min(open, close) - range, 0.01),
      volume: opts.volume ? Math.round(opts.volume * (0.6 + rand() * 0.9)) : undefined,
    };
  });
}
