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
} from "./market-data.server";

export const getOverview = createServerFn({ method: "GET" }).handler(async () => {
  return getOverviewData({
    polygonKey: process.env.POLYGON_API_KEY || undefined,
    fredKey: process.env.FRED_API_KEY || undefined,
    finnhubKey: process.env.FINNHUB_API_KEY || undefined,
  });
});

const dateStr = z.string().regex(/^\d{4}-\d{2}-\d{2}$/);
const seriesInput = z.object({
  id: z.string().refine((v): v is InstrumentId => v in INSTRUMENTS, "Unknown instrument"),
  from: dateStr.optional(),
  to: dateStr.optional(),
});

export const getSeries = createServerFn({ method: "GET" })
  .inputValidator((data: unknown) => seriesInput.parse(data))
  .handler(async ({ data }) => {
    return getSeriesData(
      data.id as InstrumentId,
      {
        polygonKey: process.env.POLYGON_API_KEY || undefined,
        fredKey: process.env.FRED_API_KEY || undefined,
        finnhubKey: process.env.FINNHUB_API_KEY || undefined,
      },
      data.from,
      data.to,
    );
  });

export const getMacro = createServerFn({ method: "GET" }).handler(async () => {
  return getMacroData({
    polygonKey: process.env.POLYGON_API_KEY || undefined,
    fredKey: process.env.FRED_API_KEY || undefined,
    finnhubKey: process.env.FINNHUB_API_KEY || undefined,
  });
});

export const getNews = createServerFn({ method: "GET" }).handler(async () => {
  return getNewsData({
    polygonKey: process.env.POLYGON_API_KEY || undefined,
    fredKey: process.env.FRED_API_KEY || undefined,
    finnhubKey: process.env.FINNHUB_API_KEY || undefined,
  });
});

export const getBreadth = createServerFn({ method: "GET" }).handler(async () => {
  return getBreadthData({
    polygonKey: process.env.POLYGON_API_KEY || undefined,
    fredKey: process.env.FRED_API_KEY || undefined,
    finnhubKey: process.env.FINNHUB_API_KEY || undefined,
  });
});

export const getProviderStatus = createServerFn({ method: "GET" }).handler(async () => {
  return getProviderStatusData({
    polygonKey: process.env.POLYGON_API_KEY || undefined,
    fredKey: process.env.FRED_API_KEY || undefined,
    finnhubKey: process.env.FINNHUB_API_KEY || undefined,
  });
});
