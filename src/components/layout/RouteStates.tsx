import { Link, useRouter, type ErrorComponentProps } from "@tanstack/react-router";

import { ErrorBlock, LoadingBlock } from "@/components/market/States";
import { useI18n } from "@/lib/i18n/context";

/** Route-level error boundary: retry re-runs loaders. */
export function RouteError({ error }: ErrorComponentProps) {
  const router = useRouter();
  console.error(error);
  return (
    <div className="mx-auto max-w-xl py-10">
      <ErrorBlock onRetry={() => router.invalidate()} />
    </div>
  );
}

export function RouteNotFound() {
  const { t } = useI18n();
  return (
    <div className="mx-auto max-w-md py-16 text-center">
      <h1 className="text-lg font-semibold">{t("notFound.title")}</h1>
      <p className="mt-2 text-sm text-muted-foreground">{t("notFound.body")}</p>
      <Link to="/" className="mt-4 inline-block text-sm font-medium text-primary hover:underline">
        {t("notFound.home")}
      </Link>
    </div>
  );
}

export function RoutePending() {
  return (
    <div className="space-y-4">
      <LoadingBlock height={36} className="max-w-sm" />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <LoadingBlock key={i} height={150} />
        ))}
      </div>
    </div>
  );
}
