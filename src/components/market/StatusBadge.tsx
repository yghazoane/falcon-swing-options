import { cva } from "class-variance-authority";
import { AlertTriangle, CircleDashed, Clock, FlaskConical, Radio, XCircle } from "lucide-react";

import type { DataStatus } from "@/lib/market/types";
import { useI18n } from "@/lib/i18n/context";
import { cn } from "@/lib/utils";

const badge = cva(
  "inline-flex shrink-0 items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium leading-4 whitespace-nowrap",
  {
    variants: {
      status: {
        live: "border-status-live/40 bg-status-live/10 text-status-live",
        delayed: "border-status-eod/40 bg-status-eod/10 text-status-eod",
        eod: "border-status-eod/40 bg-status-eod/10 text-status-eod",
        demo: "border-status-demo bg-status-demo text-status-demo-foreground font-semibold",
        unavailable: "border-border bg-muted text-status-unavailable",
        error: "border-status-error/50 bg-status-error/10 text-status-error",
        stale: "border-status-demo/50 bg-status-demo/10 text-status-demo",
      },
    },
  },
);

const ICONS = {
  live: Radio,
  delayed: Clock,
  eod: Clock,
  demo: FlaskConical,
  unavailable: CircleDashed,
  error: XCircle,
  stale: AlertTriangle,
};

export function StatusBadge({
  status,
  className,
}: {
  status: DataStatus | "stale";
  className?: string;
}) {
  const { t } = useI18n();
  const Icon = ICONS[status];
  return (
    <span className={cn(badge({ status }), className)} data-status={status}>
      <Icon className="size-3" aria-hidden />
      {t(`status.${status}`)}
    </span>
  );
}
