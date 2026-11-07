import { useMemo, type ReactNode } from "react";
import { Link } from "@tanstack/react-router";
import { useIsFetching, useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, BarChart3, Database, Globe2, Landmark, LineChart, Newspaper, RotateCw, ShieldAlert } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useNow } from "@/components/market/QuoteCard";
import { fmtDateTimeET } from "@/lib/format";
import { useI18n } from "@/lib/i18n/context";
import type { DictKey } from "@/lib/i18n/dict";
import { getMarketSession } from "@/lib/market/session";
import { overviewQuery } from "@/lib/queries";
import { cn } from "@/lib/utils";

const NAV: { to: "/" | "/breadth" | "/macro" | "/news" | "/history" | "/sources"; key: DictKey; icon: typeof Activity }[] = [
  { to: "/", key: "nav.overview", icon: Activity },
  { to: "/breadth", key: "nav.breadth", icon: BarChart3 },
  { to: "/macro", key: "nav.macro", icon: Landmark },
  { to: "/news", key: "nav.news", icon: Newspaper },
  { to: "/history", key: "nav.history", icon: LineChart },
  { to: "/sources", key: "nav.sources", icon: Database },
];

function FalconMark() {
  return (
    <svg viewBox="0 0 32 32" className="size-8 shrink-0" aria-hidden>
      <defs>
        <linearGradient id="fmi-g" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="var(--color-primary)" />
          <stop offset="1" stopColor="var(--color-violet)" />
        </linearGradient>
      </defs>
      <rect x="1" y="1" width="30" height="30" rx="8" fill="url(#fmi-g)" opacity="0.16" />
      <path d="M6 21 L13 14 L17 18 L26 9" fill="none" stroke="url(#fmi-g)" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M20 9 H26 V15" fill="none" stroke="url(#fmi-g)" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function SessionPill() {
  const { t } = useI18n();
  const now = useNow(30000);
  if (!now) return <span className="h-6 w-36 animate-pulse rounded-full bg-muted" aria-hidden />;
  const s = getMarketSession(now);
  const open = s.state === "open";
  const extended = s.state === "pre_market" || s.state === "after_hours";
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-border bg-surface px-2.5 py-1 text-[11px] text-muted-foreground">
      <span
        className={cn(
          "size-2 rounded-full",
          open ? "bg-positive animate-pulse-dot" : extended ? "bg-status-demo" : "bg-status-unavailable",
        )}
        aria-hidden
      />
      <span className="font-medium text-foreground">{t(`session.${s.state}`)}</span>
      {s.earlyClose && <span>· {t("session.early")}</span>}
      <span className="num hidden sm:inline">{t("session.nyTime", { time: s.nyTime })}</span>
    </span>
  );
}

function ConnectionPill() {
  const { t } = useI18n();
  const { data, isPending } = useQuery(overviewQuery());
  const state = useMemo(() => {
    if (!data) return "checking" as const;
    const qs = Object.values(data.quotes);
    if (qs.some((q) => q.status === "error")) return "degraded" as const;
    if (qs.some((q) => q.status === "demo")) return "partial" as const;
    return "ok" as const;
  }, [data]);
  const key: DictKey = isPending ? "conn.checking" : `conn.${state}`;
  return (
    <Link
      to="/sources"
      className={cn(
        "hidden items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium md:inline-flex",
        state === "ok" && "border-status-eod/40 text-status-eod",
        state === "partial" && "border-status-demo/40 text-status-demo",
        state === "degraded" && "border-status-error/40 text-status-error",
        state === "checking" && "border-border text-muted-foreground",
      )}
    >
      <Globe2 className="size-3" aria-hidden />
      {t(key)}
    </Link>
  );
}

function RefreshControl() {
  const { t, lang } = useI18n();
  const qc = useQueryClient();
  const fetching = useIsFetching();
  const now = useNow(15000);
  const last = useMemo(() => {
    const times = qc
      .getQueryCache()
      .getAll()
      .map((q) => q.state.dataUpdatedAt)
      .filter(Boolean);
    return times.length ? new Date(Math.max(...times)).toISOString() : null;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [qc, fetching, now]);
  return (
    <div className="flex items-center gap-2">
      <span className="hidden text-[11px] text-muted-foreground lg:inline">
        {t("topbar.lastRefresh")}: <span className="num">{now && last ? fmtDateTimeET(last, lang) : "—"}</span>
      </span>
      <Button
        size="icon"
        variant="outline"
        className="size-8"
        onClick={() => qc.invalidateQueries()}
        aria-label={t("topbar.refresh")}
        title={t("topbar.refresh")}
      >
        <RotateCw className={cn("size-4", fetching > 0 && "animate-spin")} />
      </Button>
    </div>
  );
}

function LangToggle() {
  const { t, lang, setLang } = useI18n();
  return (
    <Button
      size="sm"
      variant="outline"
      className="h-8 px-3 text-xs font-semibold"
      onClick={() => setLang(lang === "ar" ? "en" : "ar")}
      aria-label={t("lang.switchLabel")}
      lang={lang === "ar" ? "en" : "ar"}
    >
      {t("lang.switch")}
    </Button>
  );
}

function TopBar() {
  const { t } = useI18n();
  return (
    <header className="sticky top-0 z-40 border-b border-border/80 bg-background/85 backdrop-blur-md">
      <div className="mx-auto flex max-w-[1440px] items-center justify-between gap-3 px-4 py-3 sm:px-6">
        <Link to="/" className="flex min-w-0 items-center gap-2.5">
          <FalconMark />
          <div className="min-w-0 leading-tight">
            <div className="truncate text-sm font-semibold tracking-tight">
              <span className="text-brand-gradient">Falcon</span> Market Intelligence
            </div>
            <div className="hidden truncate text-[11px] text-muted-foreground sm:block">{t("app.tagline")}</div>
          </div>
        </Link>
        <div className="flex items-center gap-2">
          <SessionPill />
          <ConnectionPill />
          <RefreshControl />
          <LangToggle />
        </div>
      </div>
      <nav aria-label={t("topbar.nav")} className="mx-auto max-w-[1440px] px-2 sm:px-4">
        <ul className="scrollbar-none flex gap-1 overflow-x-auto pb-px">
          {NAV.map(({ to, key, icon: Icon }) => (
            <li key={to} className="shrink-0">
              <Link
                to={to}
                activeOptions={{ exact: to === "/" }}
                className="flex items-center gap-2 border-b-2 border-transparent px-3 py-2.5 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground sm:text-[13px]"
                activeProps={{ className: "!border-primary !text-foreground" }}
              >
                <Icon className="size-4" aria-hidden />
                {t(key)}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
    </header>
  );
}

function CoverageBanner() {
  const { t } = useI18n();
  return (
    <div className="border-b border-status-demo/25 bg-status-demo/[0.06]">
      <div className="mx-auto flex max-w-[1440px] flex-wrap items-start gap-x-4 gap-y-1.5 px-4 py-2.5 text-xs sm:px-6">
        <div className="flex items-center gap-2 font-semibold text-status-demo">
          <ShieldAlert className="size-4 shrink-0" aria-hidden />
          {t("banner.title")}
        </div>
        <p className="min-w-0 flex-1 basis-80 leading-relaxed text-muted-foreground">{t("banner.body")}</p>
        <div className="flex items-center gap-3">
          <span className="rounded-full border border-border px-2 py-0.5 text-[11px] text-muted-foreground">
            {t("topbar.realtimeOff")}
          </span>
          <Link to="/sources" className="font-medium text-primary hover:underline">
            {t("banner.cta")}
          </Link>
        </div>
      </div>
    </div>
  );
}

function Footer() {
  const { t } = useI18n();
  return (
    <footer className="mt-12 border-t border-border/80">
      <div className="mx-auto flex max-w-[1440px] flex-col gap-2 px-4 py-6 text-[11px] leading-relaxed text-muted-foreground sm:px-6">
        <p className="font-medium text-foreground/80">{t("disclaimer")}</p>
        <p>{t("sources.attr.fred")}</p>
        <p>© Falcon Market Intelligence</p>
      </div>
    </footer>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const { lang } = useI18n();
  return (
    <div className="flex min-h-screen flex-col" data-lang={lang}>
      <TopBar />
      <CoverageBanner />
      <main className="mx-auto w-full max-w-[1440px] flex-1 px-4 py-6 sm:px-6 sm:py-8">{children}</main>
      <Footer />
    </div>
  );
}
