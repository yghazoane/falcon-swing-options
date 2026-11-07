import { useMemo, useState } from "react";
import { ClientOnly } from "@tanstack/react-router";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { macd, rollingVolatility, rsi, sma } from "@/lib/analytics/indicators";
import { INSTRUMENTS } from "@/lib/market/instruments";
import type { SeriesResult } from "@/lib/market/types";
import { fmtCompact, fmtDate, fmtNum } from "@/lib/format";
import { useI18n } from "@/lib/i18n/context";
import type { DictKey } from "@/lib/i18n/dict";
import { cn } from "@/lib/utils";
import { LoadingBlock } from "./States";

type Overlay = "sma20" | "sma50" | "sma200";
type PanelId = "volume" | "rsi" | "macd" | "vol";

interface Row {
  date: string;
  close: number;
  sma20: number | null;
  sma50: number | null;
  sma200: number | null;
  volume: number | null;
  rsi: number | null;
  macd: number | null;
  signal: number | null;
  hist: number | null;
  vol: number | null;
}

const MAX_POINTS = 900;

/** Builds aligned indicator rows. Indicators use warm-up bars before `displayFrom`. */
export function buildRows(series: SeriesResult): Row[] {
  const bars = series.bars;
  const closes = bars.map((b) => b.close);
  const mode = INSTRUMENTS[series.id].mode;
  const s20 = sma(closes, 20);
  const s50 = sma(closes, 50);
  const s200 = sma(closes, 200);
  const r = rsi(closes, 14);
  const m = macd(closes);
  const v = rollingVolatility(closes, 20, mode);
  let start = series.displayFrom ? bars.findIndex((b) => b.date >= series.displayFrom!) : 0;
  if (start < 0) start = bars.length;
  const rows: Row[] = [];
  for (let i = start; i < bars.length; i++) {
    const b = bars[i]!;
    rows.push({
      date: b.date,
      close: b.close,
      sma20: s20[i] ?? null,
      sma50: s50[i] ?? null,
      sma200: s200[i] ?? null,
      volume: b.volume ?? null,
      rsi: r[i] ?? null,
      macd: m.macd[i] ?? null,
      signal: m.signal[i] ?? null,
      hist: m.hist[i] ?? null,
      vol: v[i] ?? null,
    });
  }
  if (rows.length <= MAX_POINTS) return rows;
  // Stride-sample for rendering only; always keep the latest bar.
  const stride = Math.ceil(rows.length / MAX_POINTS);
  const sampled = rows.filter((_, i) => i % stride === 0);
  const last = rows[rows.length - 1]!;
  if (sampled[sampled.length - 1] !== last) sampled.push(last);
  return sampled;
}

const OVERLAY_COLORS: Record<Overlay, string> = {
  sma20: "var(--color-chart-3)",
  sma50: "var(--color-chart-4)",
  sma200: "var(--color-chart-2)",
};

function Toggle({ on, onClick, label, color }: { on: boolean; onClick: () => void; label: string; color?: string }) {
  return (
    <button
      type="button"
      aria-pressed={on}
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-[11px] font-medium transition-colors",
        on ? "border-primary/50 bg-primary/10 text-foreground" : "border-border text-muted-foreground hover:text-foreground",
      )}
    >
      {color && <span className="h-0.5 w-3 rounded" style={{ background: color }} aria-hidden />}
      {label}
    </button>
  );
}

function ChartTooltip({
  active,
  payload,
  label,
  lang,
  decimals,
}: {
  active?: boolean;
  payload?: { name?: string; value?: number | null; color?: string; dataKey?: string }[];
  label?: string;
  lang: "ar" | "en";
  decimals: number;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-md border border-border bg-popover px-3 py-2 text-[11px] shadow-lg">
      <div className="num mb-1 text-muted-foreground">{fmtDate(label, lang)}</div>
      {payload
        .filter((p) => p.value != null)
        .map((p) => (
          <div key={p.dataKey} className="flex items-center justify-between gap-4">
            <span className="flex items-center gap-1.5 text-muted-foreground">
              <span className="size-2 rounded-full" style={{ background: p.color }} aria-hidden />
              {p.name}
            </span>
            <span className="num text-foreground">
              {p.dataKey === "volume" ? fmtCompact(p.value) : fmtNum(p.value, p.dataKey === "rsi" ? 1 : decimals)}
            </span>
          </div>
        ))}
    </div>
  );
}

const axisProps = {
  stroke: "var(--color-muted-foreground)",
  tick: { fontSize: 10, fill: "var(--color-muted-foreground)" },
  tickLine: false,
  axisLine: false,
} as const;

export function PriceChart({ series, compact = false }: { series: SeriesResult; compact?: boolean }) {
  const { t, lang } = useI18n();
  const inst = INSTRUMENTS[series.id];
  const rows = useMemo(() => buildRows(series), [series]);
  const [overlays, setOverlays] = useState<Record<Overlay, boolean>>({ sma20: false, sma50: true, sma200: true });
  const [panels, setPanels] = useState<Record<PanelId, boolean>>({
    volume: true,
    rsi: !compact,
    macd: !compact,
    vol: false,
  });
  const isDemo = series.status === "demo";
  const decimals = inst.decimals;
  const fmtTick = (d: string) => fmtDate(d, lang, { day: undefined, month: "short", year: "2-digit" });
  const yFmt = (v: number) => (Math.abs(v) >= 10000 ? fmtCompact(v) : fmtNum(v, Math.abs(v) < 20 ? 2 : 0));
  const sync = `sync-${series.id}`;

  const overlayLabels: Record<Overlay, DictKey> = { sma20: "chart.sma20", sma50: "chart.sma50", sma200: "chart.sma200" };
  const panelLabels: Record<PanelId, DictKey> = {
    volume: "chart.volume",
    rsi: "chart.rsi",
    macd: "chart.macdLine",
    vol: inst.mode === "price" ? "chart.volatility" : "chart.volatilityLevel",
  };

  const tooltip = (props: object) => <ChartTooltip {...props} lang={lang} decimals={decimals} />;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[11px] text-muted-foreground">{t("chart.overlays")}:</span>
          {(Object.keys(overlays) as Overlay[]).map((k) => (
            <Toggle
              key={k}
              on={overlays[k]}
              color={OVERLAY_COLORS[k]}
              label={t(overlayLabels[k])}
              onClick={() => setOverlays((o) => ({ ...o, [k]: !o[k] }))}
            />
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[11px] text-muted-foreground">{t("chart.panels")}:</span>
          {(Object.keys(panels) as PanelId[]).map((k) => (
            <Toggle
              key={k}
              on={panels[k]}
              label={k === "vol" ? t("history.m.vol") : t(panelLabels[k])}
              onClick={() => setPanels((p) => ({ ...p, [k]: !p[k] }))}
            />
          ))}
        </div>
      </div>

      <ClientOnly fallback={<LoadingBlock height={compact ? 300 : 520} />}>
        {/* Charts keep a left-to-right time axis in both languages (finance convention). */}
        <div dir="ltr" className={cn("relative space-y-2", isDemo && "rounded-md demo-surface p-1")}>
          {isDemo && (
            <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center">
              <span className="rotate-[-12deg] rounded border-2 border-status-demo/50 px-4 py-1 text-xl font-bold uppercase tracking-widest text-status-demo/50 sm:text-3xl">
                {t("status.demo")}
              </span>
            </div>
          )}
          <div style={{ height: compact ? 260 : 320 }} aria-label={`${inst.symbol} ${t("chart.price")}`} role="img">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={rows} syncId={sync} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="var(--color-grid)" vertical={false} />
                <XAxis dataKey="date" {...axisProps} tickFormatter={fmtTick} minTickGap={48} />
                <YAxis {...axisProps} domain={["auto", "auto"]} tickFormatter={yFmt} width={56} orientation="right" />
                <Tooltip content={tooltip} cursor={{ stroke: "var(--color-muted-foreground)", strokeDasharray: "3 3" }} />
                <Line
                  type="monotone"
                  dataKey="close"
                  name={t("chart.close")}
                  stroke="var(--color-chart-1)"
                  strokeWidth={1.8}
                  dot={false}
                  isAnimationActive={false}
                />
                {(Object.keys(overlays) as Overlay[]).map((k) =>
                  overlays[k] ? (
                    <Line
                      key={k}
                      type="monotone"
                      dataKey={k}
                      name={t(overlayLabels[k])}
                      stroke={OVERLAY_COLORS[k]}
                      strokeWidth={1.2}
                      dot={false}
                      isAnimationActive={false}
                      connectNulls
                    />
                  ) : null,
                )}
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          {panels.volume &&
            (series.hasVolume ? (
              <div style={{ height: 80 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={rows} syncId={sync} margin={{ top: 0, right: 8, left: 0, bottom: 0 }}>
                    <XAxis dataKey="date" hide />
                    <YAxis {...axisProps} tickFormatter={fmtCompact} width={56} orientation="right" />
                    <Tooltip content={tooltip} cursor={{ fill: "var(--color-accent)" }} />
                    <Bar dataKey="volume" name={t("chart.volume")} fill="var(--color-chart-1)" opacity={0.45} isAnimationActive={false} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <p dir={lang === "ar" ? "rtl" : "ltr"} className="rounded-md border border-dashed border-border px-3 py-2 text-[11px] text-muted-foreground">
                {t("chart.noVolume")}
              </p>
            ))}

          {panels.rsi && (
            <SubPanel label={t("chart.rsi")} height={110}>
              <LineChart data={rows} syncId={sync} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="var(--color-grid)" vertical={false} />
                <XAxis dataKey="date" hide />
                <YAxis {...axisProps} domain={[0, 100]} ticks={[30, 50, 70]} width={56} orientation="right" />
                <ReferenceLine y={70} stroke="var(--color-negative)" strokeDasharray="3 3" strokeOpacity={0.6} />
                <ReferenceLine y={30} stroke="var(--color-positive)" strokeDasharray="3 3" strokeOpacity={0.6} />
                <Tooltip content={tooltip} />
                <Line type="monotone" dataKey="rsi" name="RSI" stroke="var(--color-violet)" strokeWidth={1.4} dot={false} isAnimationActive={false} connectNulls />
              </LineChart>
            </SubPanel>
          )}

          {panels.macd && (
            <SubPanel label={t("chart.macd")} height={120}>
              <ComposedChart data={rows} syncId={sync} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="var(--color-grid)" vertical={false} />
                <XAxis dataKey="date" hide />
                <YAxis {...axisProps} tickFormatter={(v: number) => fmtNum(v, Math.abs(v) < 5 ? 2 : 0)} width={56} orientation="right" />
                <ReferenceLine y={0} stroke="var(--color-border)" />
                <Tooltip content={tooltip} />
                <Bar dataKey="hist" name={t("chart.hist")} fill="var(--color-muted-foreground)" opacity={0.5} isAnimationActive={false} />
                <Line type="monotone" dataKey="macd" name={t("chart.macdLine")} stroke="var(--color-chart-1)" strokeWidth={1.3} dot={false} isAnimationActive={false} connectNulls />
                <Line type="monotone" dataKey="signal" name={t("chart.signal")} stroke="var(--color-chart-4)" strokeWidth={1.3} dot={false} isAnimationActive={false} connectNulls />
              </ComposedChart>
            </SubPanel>
          )}

          {panels.vol && (
            <SubPanel label={t(panelLabels.vol)} height={110}>
              <LineChart data={rows} syncId={sync} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="var(--color-grid)" vertical={false} />
                <XAxis dataKey="date" hide />
                <YAxis {...axisProps} tickFormatter={(v: number) => fmtNum(v, 1)} width={56} orientation="right" />
                <Tooltip content={tooltip} />
                <Line type="monotone" dataKey="vol" name={t("history.m.vol")} stroke="var(--color-chart-5)" strokeWidth={1.4} dot={false} isAnimationActive={false} connectNulls />
              </LineChart>
            </SubPanel>
          )}
          <p dir={lang === "ar" ? "rtl" : "ltr"} className="text-[10px] text-muted-foreground">
            {t("chart.timeAxis")}
            {!series.hasVolume && inst.kind === "index" ? ` · ${t("chart.indexCloseOnly")}` : ""}
          </p>
        </div>
      </ClientOnly>
    </div>
  );
}

function SubPanel({ label, height, children }: { label: string; height: number; children: React.ReactElement }) {
  return (
    <div className="border-t border-border/60 pt-1">
      <div className="px-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">{label}</div>
      <div style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          {children}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
