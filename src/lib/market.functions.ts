// Server functions: the only bridge between the UI and provider adapters.
// API keys are read from server-side environment variables inside each handler and never returned.
import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";

import { INSTRUMENTS } from "./market/instruments";
import type { InstrumentId } from "./market/types";
import {
  getBreadthData,
  getMacroData,
  getNewsData,
  getOverviewData,
  getProviderStatusData,
  getSeriesData,
  type ProviderEnv,
} from "./market-data.server";

/** Must be called inside a handler: env vars are injected per request. */
function readEnv(): ProviderEnv {
  const env: ProviderEnv = {};
  const polygon = process.env["POLYGON_API_KEY"];
  const fred = process.env["FRED_API_KEY"];
  const finnhub = process.env["FINNHUB_API_KEY"];
  if (polygon) env.polygonKey = polygon;
  if (fred) env.fredKey = fred;
  if (finnhub) env.finnhubKey = finnhub;
  return env;
}

export const getOverview = createServerFn({ method: "GET" }).handler(async () => getOverviewData(readEnv()));

const dateStr = z.string().regex(/^\d{4}-\d{2}-\d{2}$/);
const seriesInput = z.object({
  id: z.string().refine((v) => v in INSTRUMENTS, "Unknown instrument"),
  from: dateStr.optional(),
  to: dateStr.optional(),
});

export const getSeries = createServerFn({ method: "GET" })
  .inputValidator((data: unknown) => seriesInput.parse(data))
  .handler(async ({ data }) => getSeriesData(data.id as InstrumentId, readEnv(), data.from, data.to));

export const getMacro = createServerFn({ method: "GET" }).handler(async () => getMacroData(readEnv()));

export const getNews = createServerFn({ method: "GET" }).handler(async () => getNewsData(readEnv()));

export const getBreadth = createServerFn({ method: "GET" }).handler(async () => getBreadthData(readEnv()));

export const getProviderStatus = createServerFn({ method: "GET" }).handler(async () =>
  getProviderStatusData(readEnv()),
);
