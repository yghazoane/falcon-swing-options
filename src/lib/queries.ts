import { queryOptions } from "@tanstack/react-query";

import {
  getBreadth,
  getMacro,
  getNews,
  getOverview,
  getProviderStatus,
  getSeries,
} from "./market.functions";
import type { InstrumentId } from "./market/types";

const FIVE_MIN = 5 * 60 * 1000;

export const overviewQuery = () =>
  queryOptions({
    queryKey: ["overview"],
    queryFn: () => getOverview(),
    staleTime: FIVE_MIN,
    refetchInterval: FIVE_MIN,
  });

export const seriesQuery = (id: InstrumentId, from?: string, to?: string) =>
  queryOptions({
    queryKey: ["series", id, from ?? null, to ?? null],
    queryFn: () => getSeries({ data: { id, from, to } }),
    staleTime: FIVE_MIN,
  });

export const macroQuery = () =>
  queryOptions({ queryKey: ["macro"], queryFn: () => getMacro(), staleTime: 15 * 60 * 1000 });

export const newsQuery = () =>
  queryOptions({ queryKey: ["news"], queryFn: () => getNews(), staleTime: FIVE_MIN, refetchInterval: FIVE_MIN });

export const breadthQuery = () =>
  queryOptions({ queryKey: ["breadth"], queryFn: () => getBreadth(), staleTime: FIVE_MIN });

export const providerStatusQuery = () =>
  queryOptions({ queryKey: ["providers"], queryFn: () => getProviderStatus(), staleTime: 60 * 1000 });

/** Inclusive ISO start date for a range preset relative to `end`. */
export type RangePreset = "1M" | "3M" | "6M" | "YTD" | "1Y" | "3Y" | "5Y" | "10Y" | "MAX";
export function rangeStart(preset: RangePreset, end: Date): string | undefined {
  const d = new Date(Date.UTC(end.getUTCFullYear(), end.getUTCMonth(), end.getUTCDate()));
  switch (preset) {
    case "1M":
      d.setUTCMonth(d.getUTCMonth() - 1);
      break;
    case "3M":
      d.setUTCMonth(d.getUTCMonth() - 3);
      break;
    case "6M":
      d.setUTCMonth(d.getUTCMonth() - 6);
      break;
    case "YTD":
      return `${d.getUTCFullYear()}-01-01`;
    case "1Y":
      d.setUTCFullYear(d.getUTCFullYear() - 1);
      break;
    case "3Y":
      d.setUTCFullYear(d.getUTCFullYear() - 3);
      break;
    case "5Y":
      d.setUTCFullYear(d.getUTCFullYear() - 5);
      break;
    case "10Y":
      d.setUTCFullYear(d.getUTCFullYear() - 10);
      break;
    case "MAX":
      return undefined;
  }
  return d.toISOString().slice(0, 10);
}
