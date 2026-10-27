import type { ReactNode } from "react";

/* Shared primitives for the administrative UI. Colours come from the tokens
 * in index.css; nothing here should invent its own palette. */

const BUTTON_BASE =
  "inline-flex items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-forest-700";

const BUTTON_VARIANTS = {
  primary: "bg-forest-700 text-white hover:bg-forest-800",
  secondary: "border border-line-strong bg-surface text-ink hover:bg-canvas",
} as const;

type ButtonProps = {
  children: ReactNode;
  href?: string;
  onClick?: () => void;
  disabled?: boolean;
  /** Explanation shown on hover and announced to assistive technology. */
  disabledReason?: string;
  variant?: keyof typeof BUTTON_VARIANTS;
  type?: "button" | "submit";
  className?: string;
};

export function Button({
  children,
  href,
  onClick,
  disabled = false,
  disabledReason,
  variant = "primary",
  type = "button",
  className = "",
}: ButtonProps) {
  if (disabled) {
    return (
      <button
        type="button"
        disabled
        title={disabledReason}
        className={`${BUTTON_BASE} cursor-not-allowed border border-line bg-canvas text-ink-mute ${className}`}
      >
        {children}
        {disabledReason ? <span className="sr-only"> — unavailable: {disabledReason}</span> : null}
      </button>
    );
  }

  if (href) {
    return (
      <a href={href} className={`${BUTTON_BASE} ${BUTTON_VARIANTS[variant]} ${className}`}>
        {children}
      </a>
    );
  }

  return (
    <button
      type={type}
      onClick={onClick}
      className={`${BUTTON_BASE} ${BUTTON_VARIANTS[variant]} ${className}`}
    >
      {children}
    </button>
  );
}

/** Persistent provenance label for synthetic demo data. */
export function DemoTag({ label = "Synthetic data" }: { label?: string }) {
  return (
    <span className="inline-flex shrink-0 items-center rounded-sm border border-line-strong bg-canvas px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wider text-ink-mute">
      {label}
    </span>
  );
}

export type StatusTone = "neutral" | "success" | "warning" | "info";

const STATUS_TONE_CLASSES: Record<StatusTone, string> = {
  neutral: "border-line-strong bg-canvas text-ink-soft",
  success: "border-forest-200 bg-forest-50 text-forest-800",
  warning: "border-warning-100 bg-warning-50 text-warning-600",
  info: "border-info-100 bg-info-50 text-info-700",
};

const BATCH_STATES: Record<string, { label: string; tone: StatusTone }> = {
  CREATED: { label: "Draft", tone: "neutral" },
  UPLOADED: { label: "Processing", tone: "info" },
  VALIDATING: { label: "Processing", tone: "info" },
  VALIDATED: { label: "Ready", tone: "success" },
  SUBMITTED_FOR_REVIEW: { label: "Submitted for review", tone: "success" },
  VALIDATION_FAILED: { label: "Needs review", tone: "warning" },
};

export function batchStatus(state: string): { label: string; tone: StatusTone } {
  return BATCH_STATES[state] ?? { label: state, tone: "neutral" };
}

/**
 * A capability or status label. Text plus a pale tint, never colour alone;
 * sized for a row or beside a value, not above a heading.
 */
export function StatusTag({
  tone = "neutral",
  children,
}: {
  tone?: StatusTone;
  children: ReactNode;
}) {
  return (
    <span
      className={`inline-flex shrink-0 items-center rounded-sm border px-1.5 py-0.5 text-[11px] font-medium whitespace-nowrap ${STATUS_TONE_CLASSES[tone]}`}
    >
      {children}
    </span>
  );
}

/**
 * The one-sentence empty state: the panel keeps its frame and header, and the
 * message spans the block. `title` names what is missing, the children say why.
 */
export function EmptyState({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="rounded-md border border-dashed border-line-strong px-4 py-5 text-center">
      <p className="text-sm font-medium text-ink">{title}</p>
      <p className="mx-auto mt-1 max-w-lg text-xs leading-relaxed text-ink-soft">
        {children}
      </p>
    </div>
  );
}

/** Compact label/value rows for one record's fields. */
export function MetaList({
  items,
}: {
  items: { label: string; value: ReactNode }[];
}) {
  return (
    <dl className="divide-y divide-line text-sm">
      {items.map((item) => (
        <div key={item.label} className="flex flex-wrap gap-x-3 gap-y-0.5 py-1.5">
          <dt className="w-40 shrink-0 text-xs text-ink-mute">{item.label}</dt>
          <dd className="min-w-0 flex-1 text-ink">{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}

/** A missing value is a quiet dash, never a blank cell. */
export function Dash() {
  return <span className="text-ink-mute">—</span>;
}

/** Status is always text plus colour, never colour alone. */
export function StatusBadge({ state }: { state: string }) {
  const { label, tone } = batchStatus(state);
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-sm border px-2 py-0.5 text-xs font-medium ${STATUS_TONE_CLASSES[tone]}`}
    >
      <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-current" />
      {label}
    </span>
  );
}

type StatCardProps = {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
};

/**
 * A compact metric with a provenance tag. The value must be computed from
 * scoped API data; this component never supplies a placeholder count.
 */
export function StatCard({ label, value, hint }: StatCardProps) {
  return (
    <div className="rounded-md border border-line bg-surface p-4">
      <div className="flex items-start justify-between gap-2">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-ink-mute">
          {label}
        </p>
        <DemoTag />
      </div>
      <p className="mt-2 text-2xl font-semibold tracking-tight text-ink">{value}</p>
      {hint ? <p className="mt-1 text-xs text-ink-soft">{hint}</p> : null}
    </div>
  );
}

type AlertTone = "error" | "warning" | "success" | "info";

const ALERT_TONES: Record<AlertTone, string> = {
  error: "border-error-100 bg-error-50 text-error-600",
  warning: "border-warning-100 bg-warning-50 text-warning-600",
  success: "border-forest-200 bg-forest-50 text-forest-800",
  info: "border-info-100 bg-info-50 text-info-700",
};

/**
 * Inline message. Errors are announced (`role="alert"`) and are never used to
 * replace the data that failed to load.
 */
export function Alert({
  tone = "error",
  title,
  children,
  action,
}: {
  tone?: AlertTone;
  title?: ReactNode;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div
      role={tone === "error" ? "alert" : "status"}
      className={`flex flex-wrap items-start justify-between gap-3 rounded-md border px-4 py-3 text-sm ${ALERT_TONES[tone]}`}
    >
      <div className="min-w-0">
        {title ? <p className="font-medium">{title}</p> : null}
        <div className={title ? "mt-0.5" : undefined}>{children}</div>
      </div>
      {/* max-w-full lets the action area wrap onto its own line on a phone
          instead of pushing the page wider than the viewport. */}
      {action ? <div className="max-w-full">{action}</div> : null}
    </div>
  );
}

export function PageHeader({
  title,
  description,
  action,
}: {
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div className="min-w-0">
        <h1 className="text-2xl font-semibold tracking-tight text-ink">{title}</h1>
        {description ? (
          <p className="mt-1 max-w-2xl text-sm text-ink-soft">{description}</p>
        ) : null}
      </div>
      {/* max-w-full lets the action area wrap onto its own line on a phone
          instead of pushing the page wider than the viewport. */}
      {action ? <div className="max-w-full">{action}</div> : null}
    </div>
  );
}
