import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { keepPreviousData, useQuery, useSuspenseQuery } from "@tanstack/react-query";

import { RouteError, RouteNotFound, RoutePending } from "@/components/layout/RouteStates";
import { PageHeader, Panel, SectionTitle, Segmented, SourceLink } from "@/components/market/Panel";
import { PriceChart } from "@/components/market/PriceChart";
import { QuoteCard } from "@/components/market/QuoteCard";
import { ErrorBlock, LoadingBlock } from "@/components/market/States";
import { StatusBadge } from "@/components/market/StatusBadge";
import { fmtDate, fmtDateTimeET } from "@/lib/format";
import { useDynamicT, useI18n } from "@/lib/i18n/context";
import { CHART_IDS, CONTEXT_IDS, INSTRUMENTS, OVERVIEW_IDS, PROXY_IDS } from "@/lib/market/instruments";
import type { InstrumentId } from "@/lib/market/types";
import { overviewQuery, rangeStart, seriesQuery, type RangePreset } from "@/lib/queries";

const RANGES: RangePreset[] = ["1M", "3M", "6M", "YTD", "1Y", "3Y", "5Y", "MAX"];

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Market Overview — Falcon Market Intelligence" },
      {
        name: "description",
        content: "S&P 500 and Nasdaq-100 overview with ETF proxies, VIX, Treasury yields and dollar context, with clear source and freshness labels.",
      },
      { property: "og:title", content: "Market Overview — Falcon Market Intelligence" },
      {
        property: "og:description",
        content: "Educational U.S. market overview: indices, ETF proxies, volatility and Treasury yields with sourced end-of-day data.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  loader: ({ context }) => {
    context.queryClient.prefetchQuery(seriesQuery("SPX", rangeStart("1Y", new Date())));
    return context.queryClient.ensureQueryData(overviewQuery());
  },
  pendingComponent: RoutePending,
  errorComponent: RouteError,
  notFoundComponent: RouteNotFound,
  component: Overview,
});

function Overview() {
  const { t, lang } = useI18n();
  const { data } = useSuspenseQuery(overviewQuery());
  const q = (id: InstrumentId) => data.quotes[id];

  return (
    <div className="space-y-8">
      <PageHeader title={t("overview.title")} subtitle={t("overview.subtitle")}>
        <span className="text-[11px] text-muted-foreground">
          {t("topbar.lastRefresh")}: <span className="num">{fmtDateTimeET(data.generatedAt, lang)}</span>
        </span>
      </PageHeader>

      <section>
        <SectionTitle>{t("overview.indices")}</SectionTitle>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {OVERVIEW_IDS.map((id) => (
            <QuoteCard key={id} quote={q(id)} />
          ))}
        </div>
        {INSTRUMENTS.DXY.licenseNote && (
          <p className="mt-2 text-[11px] text-muted-foreground">{INSTRUMENTS.DXY.licenseNote[lang]}</p>
        )}
      </section>

      <section>
        <SectionTitle>{t("overview.proxies")}</SectionTitle>
        <div className="grid gap-3 sm:grid-cols-2">
          {PROXY_IDS.map((id) => (
            <QuoteCard key={id} quote={q(id)} />
          ))}
        </div>
      </section>

      <ChartSection />

      <section>
        <SectionTitle>{t("overview.context")}</SectionTitle>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
          {CONTEXT_IDS.map((id) => (
            <QuoteCard key={id} quote={q(id)} />
          ))}
        </div>
        <p className="mt-2 text-[11px] text-muted-foreground">{t("overview.globalNote")}</p>
      </section>
    </div>
  );
}

function ChartSection() {
  const { t, lang } = useI18n();
  const dt = useDynamicT();
  const [id, setId] = useState<InstrumentId>("SPX");
  const [range, setRange] = useState<RangePreset>("1Y");
  const query = useQuery({ ...seriesQuery(id, rangeStart(range, new Date())), placeholderData: keepPreviousData });
  const s = query.data;

  return (
    <Panel
      title={t("overview.chart")}
      subtitle={INSTRUMENTS[id].name[lang]}
      actions={
        <>
          <Segmented
            label={t("chart.instrument")}
            value={id}
            onChange={setId}
            options={CHART_IDS.map((v) => ({ value: v, label: INSTRUMENTS[v].symbol }))}
          />
          <Segmented label={t("chart.range")} value={range} onChange={setRange} options={RANGES.map((r) => ({ value: r, label: r }))} />
        </>
      }
      footer={
        s ? (
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
            <StatusBadge status={s.status} />
            <span>
              {t("common.asOf")} <span className="num">{fmtDate(s.asOf, lang)}</span>
            </span>
            <span>
              {t("common.source")}: <SourceLink name={s.providerName} url={s.sourceUrl} />
            </span>
            {s.note && <span>{dt(`note.${s.note}`)}</span>}
          </div>
        ) : null
      }
    >
      {query.isError ? (
        <ErrorBlock onRetry={() => query.refetch()} />
      ) : !s ? (
        <LoadingBlock height={420} />
      ) : s.bars.length < 2 ? (
        <ErrorBlock message={s.note ? dt(`note.${s.note}`) : t("common.noData")} onRetry={() => query.refetch()} />
      ) : (
        <PriceChart series={s} compact />
      )}
    </Panel>
  );
}
