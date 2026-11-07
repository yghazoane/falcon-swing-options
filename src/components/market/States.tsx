import type { ReactNode } from "react";
import { AlertOctagon, CircleDashed, Inbox, RotateCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useI18n } from "@/lib/i18n/context";
import { cn } from "@/lib/utils";

export function LoadingBlock({ height = 240, className }: { height?: number; className?: string }) {
  const { t } = useI18n();
  return (
    <div className={cn("relative", className)} style={{ height }} aria-busy="true">
      <Skeleton className="absolute inset-0 rounded-md bg-muted/60" />
      <span className="sr-only">{t("common.loading")}</span>
    </div>
  );
}

export function ErrorBlock({ message, onRetry }: { message?: string; onRetry?: () => void }) {
  const { t } = useI18n();
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-md border border-status-error/30 bg-status-error/5 px-4 py-8 text-center">
      <AlertOctagon className="size-6 text-status-error" aria-hidden />
      <p className="text-sm text-foreground">{t("common.loadError")}</p>
      {message && <p className="text-xs text-muted-foreground">{message}</p>}
      {onRetry && (
        <Button size="sm" variant="outline" onClick={onRetry}>
          <RotateCw /> {t("common.retry")}
        </Button>
      )}
    </div>
  );
}

export function EmptyBlock({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-md border border-dashed border-border px-4 py-10 text-center">
      <Inbox className="size-6 text-muted-foreground" aria-hidden />
      <p className="text-sm text-muted-foreground">{message}</p>
    </div>
  );
}

export function UnavailableBlock({ reason, detail, compact }: { reason: string; detail?: ReactNode; compact?: boolean }) {
  return (
    <div
      className={cn(
        "flex flex-col items-start gap-2 rounded-md border border-dashed border-border bg-muted/30",
        compact ? "px-3 py-3" : "px-4 py-6",
      )}
    >
      <div className="flex items-center gap-2 text-sm font-medium text-status-unavailable">
        <CircleDashed className="size-4" aria-hidden />
        <span>—</span>
      </div>
      <p className="text-xs leading-relaxed text-muted-foreground">{reason}</p>
      {detail && <div className="text-[11px] leading-relaxed text-muted-foreground/80">{detail}</div>}
    </div>
  );
}
