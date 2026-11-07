import type { ReactNode } from "react";
import { ExternalLink } from "lucide-react";

import { cn } from "@/lib/utils";

export function Panel({
  title,
  subtitle,
  actions,
  children,
  footer,
  className,
  bodyClassName,
}: {
  title?: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  return (
    <section className={cn("panel flex flex-col", className)}>
      {(title || actions) && (
        <header className="flex flex-wrap items-start justify-between gap-3 border-b border-border/70 px-4 py-3 sm:px-5">
          <div className="min-w-0">
            {title && <h2 className="text-sm font-semibold tracking-wide text-foreground">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-xs text-muted-foreground">{subtitle}</p>}
          </div>
          {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
        </header>
      )}
      <div className={cn("flex-1 p-4 sm:p-5", bodyClassName)}>{children}</div>
      {footer && (
        <footer className="border-t border-border/70 px-4 py-2.5 text-[11px] text-muted-foreground sm:px-5">
          {footer}
        </footer>
      )}
    </section>
  );
}

export function SourceLink({ name, url }: { name: string; url?: string | undefined }) {
  if (!url) return <span>{name}</span>;
  return (
    <a
      href={url}
      target="_blank"
      rel="noreferrer"
      className="inline-flex items-center gap-1 text-muted-foreground underline-offset-2 hover:text-primary hover:underline"
    >
      {name}
      <ExternalLink className="size-3" aria-hidden />
    </a>
  );
}

export function PageHeader({ title, subtitle, children }: { title: string; subtitle?: string; children?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-foreground sm:text-2xl">{title}</h1>
        {subtitle && <p className="mt-1 max-w-2xl text-sm text-muted-foreground">{subtitle}</p>}
      </div>
      {children}
    </div>
  );
}

export function SectionTitle({ children, aside }: { children: ReactNode; aside?: ReactNode }) {
  return (
    <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
      <h2 className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">{children}</h2>
      {aside}
    </div>
  );
}

export function Segmented<T extends string>({
  options,
  value,
  onChange,
  label,
}: {
  options: { value: T; label: string }[];
  value: T;
  onChange: (v: T) => void;
  label: string;
}) {
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex flex-wrap gap-1 rounded-lg border border-border bg-surface p-1">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={value === o.value}
          onClick={() => onChange(o.value)}
          className={cn(
            "rounded-md px-2.5 py-1 text-xs font-medium transition-colors",
            value === o.value
              ? "bg-primary text-primary-foreground shadow"
              : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
