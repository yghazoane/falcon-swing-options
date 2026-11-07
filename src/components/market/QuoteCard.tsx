import { useEffect, useState } from "react";

import { INSTRUMENTS } from "@/lib/market/instruments";
import type { Quote } from "@/lib/market/types";
import { businessDaysSince, isStale } from "@/lib/market/session";
import { fmtDate, fmtNum, fmtSigned } from "@/lib/format";
import { useDynamicT, useI18n } from "@/lib/i18n/context";
import { cn } from "@/lib/utils";
import { SourceLink } from "./Panel";
import { StatusBadge } from "./StatusBadge";

export function Sparkline({ values, className }: { values: number[]; className?: string }) {
  if (values.length < 2) return <div className={cn("h-8", className)} />;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const pts = values.map((v, i) => `${(i / (values.length - 1)) * 100},${28 - ((v - min) / span) * 26}`).join(" ");
  const up = (values[values.length - 1] ?? 0) >= (values[0] ?? 0);
  return (
    <svg viewBox="0 0 100 30" preserveAspectRatio="none" className={cn("h-8 w-full", className)} aria-hidden>
      <polyline
        points={pts}
        fill="none"
        strokeWidth={1.5}
        vectorEffect="non-scaling-stroke"
        className={up ? "stroke-positive" : "stroke-negative"}
      />
    </svg>
  );
}

function formatValue(q: Quote) {
  const inst = INSTRUMENTS[q.id];
  if (q.value == null) return "—";
  if (inst.unit === "%") return `${fmtNum(q.value, inst.decimals)}%`;
  if (inst.unit === "pp") return `${fmtSigned(q.value, 2)} pp`;
  if (inst.unit === "$") return `$${fmtNum(q.value, inst.decimals)}`;
  return fmtNum(q.value, inst.decimals);
}

function formatChange(q: Quote, bpLabel: string) {
  const inst = INSTRUMENTS[q.id];
  if (q.change == null) return { text: "—", sign: 0 };
  const sign = Math.sign(q.change);
  if (inst.unit === "%" || inst.unit === "pp") return { text: `${fmtSigned(q.change * 100, 0)} ${bpLabel}`, sign };
  return { text: `${fmtSigned(q.change, inst.decimals)} (${fmtSigned(q.changePct, 2, "%")})`, sign };
}

export function useNow(intervalMs = 60000) {
  const [now, setNow] = useState<Date | null>(null);
  useEffect(() => {
    setNow(new Date());
    const id = window.setInterval(() => setNow(new Date()), intervalMs);
    return () => window.clearInterval(id);
  }, [intervalMs]);
  return now;
}

export function QuoteCard({ quote, className }: { quote: Quote; className?: string }) {
  const { t, lang } = useI18n();
  const dt = useDynamicT();
  const now = useNow();
  const inst = INSTRUMENTS[quote.id];
  const isDemo = quote.status === "demo";
  const stale = now && quote.status !== "demo" && isStale(quote.asOf, now);
  const change = formatChange(quote, t("common.bp"));
  const proxyName = inst.proxyOf ? INSTRUMENTS[inst.proxyOf].name[lang] : null;

  return (
    <article
      className={cn("panel relative flex flex-col gap-2 overflow-hidden p-4", isDemo && "demo-surface border-status-demo/40", className)}
      aria-label={inst.name[lang]}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="num text-xs font-semibold text-primary">{inst.symbol}</span>
            <span className="text-[10px] uppercase tracking-wider text-muted-foreground">{t(`kind.${inst.kind}`)}</span>
          </div>
          <h3 className="mt-0.5 truncate text-xs text-muted-foreground" title={inst.name[lang]}>
            {inst.name[lang]}
          </h3>
        </div>
        <StatusBadge status={quote.status} />
      </div>

      <div className="flex items-end justify-between gap-2">
        <div>
          <div className={cn("num text-2xl font-semibold tracking-tight", quote.value == null && "text-muted-foreground")}>
            {formatValue(quote)}
          </div>
          <div
            className={cn(
              "num text-xs font-medium",
              change.sign > 0 ? "text-positive" : change.sign < 0 ? "text-negative" : "text-muted-foreground",
            )}
          >
            {change.text}
          </div>
        </div>
        <Sparkline values={quote.spark} className="max-w-24" />
      </div>

      {isDemo && <p className="text-[11px] font-medium text-status-demo">{t("common.demoValue")}</p>}
      {proxyName && <p className="text-[11px] text-muted-foreground">{t("common.proxyOf", { name: proxyName })}</p>}
      {quote.status === "error" && quote.note && <p className="text-[11px] text-status-error">{dt(`note.${quote.note}`)}</p>}
      {stale && quote.asOf && (
        <div className="flex items-center gap-2">
          <StatusBadge status="stale" />
          <span className="text-[11px] text-muted-foreground">
            {t("common.staleWarning", { days: businessDaysSince(quote.asOf, now) })}
          </span>
        </div>
      )}

      <div className="mt-auto flex flex-wrap items-center justify-between gap-x-3 gap-y-1 border-t border-border/60 pt-2 text-[11px] text-muted-foreground">
        <span>
          {t("common.asOf")} <span className="num">{fmtDate(quote.asOf, lang)}</span>
        </span>
        <SourceLink name={quote.providerName} url={quote.sourceUrl} />
      </div>
    </article>
  );
}
