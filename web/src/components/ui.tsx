"use client";

import Link from "next/link";
import { useLang } from "@/lib/lang-context";

/** The shared header with the language switch (fa/en). */
export function Header() {
  const { lang, setLang, t } = useLang();
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3">
        <Link href="/" className="font-bold text-emerald-700">
          {t("appName")}
        </Link>
        <nav className="flex items-center gap-3 text-sm">
          <Link href="/new" className="text-slate-600 hover:text-emerald-700">
            {t("ctaNewTrip")}
          </Link>
          <Link href="/trips" className="text-slate-600 hover:text-emerald-700">
            {t("myTrips")}
          </Link>
          <button
            type="button"
            onClick={() => setLang(lang === "fa" ? "en" : "fa")}
            className="rounded-md border border-slate-300 px-2 py-1 font-mono text-xs"
            aria-label="Switch language"
          >
            {lang === "fa" ? "EN" : "فا"}
          </button>
        </nav>
      </div>
    </header>
  );
}

/** Coloured provenance badge: confirmed/estimated/inferred/unavailable. */
const STATUS_STYLES: Record<string, string> = {
  confirmed: "bg-emerald-100 text-emerald-800",
  estimated: "bg-amber-100 text-amber-800",
  inferred: "bg-sky-100 text-sky-800",
  unavailable: "bg-slate-200 text-slate-600",
};

export function StatusBadge({ status }: { status: string }) {
  const { lang, t } = useLang();
  const key = (["confirmed", "estimated", "inferred", "unavailable"] as const).includes(
    status as "confirmed",
  )
    ? (status as "confirmed" | "estimated" | "inferred" | "unavailable")
    : "estimated";
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-xs ${STATUS_STYLES[key]}`}
      data-testid="status-badge"
    >
      {t(key)}
      {lang === "fa" ? "" : ""}
    </span>
  );
}

/** Spinner + label, used while the graph runs. */
export function PlanningIndicator({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 text-slate-600" role="status">
      <span className="h-5 w-5 animate-spin rounded-full border-2 border-emerald-600 border-t-transparent" />
      <span>{label}</span>
    </div>
  );
}

/** Inline error box. */
export function ErrorBox({ message }: { message: string }) {
  return (
    <div
      role="alert"
      className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
    >
      {message}
    </div>
  );
}
