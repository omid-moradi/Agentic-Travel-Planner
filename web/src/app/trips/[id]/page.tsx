"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ErrorBox, Header } from "@/components/ui";
import { ItineraryView } from "@/components/itinerary-view";
import { api, ApiClientError } from "@/lib/api";
import { localiseDigits } from "@/lib/i18n";
import { useLang } from "@/lib/lang-context";

interface TraceItem {
  node: string;
  status: string;
  created_at: string;
}

export default function TripDetailPage() {
  const { lang, t } = useLang();
  const params = useParams<{ id: string }>();
  const tripId = params?.id ?? "";
  const [error, setError] = useState<string | null>(null);
  const [payload, setPayload] = useState<Parameters<typeof ItineraryView>[0]["payload"] | null>(null);
  const [trace, setTrace] = useState<TraceItem[]>([]);
  const [busy, setBusy] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);
  const [shareUrl, setShareUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!tripId) return;
    let cancelled = false;
    void (async () => {
      try {
        const itinerary = await api.getItinerary(tripId);
        const traceResponse = await api.getTrace(tripId);
        if (cancelled) return;
        setPayload(itinerary.payload);
        setTrace(traceResponse.items);
        setError(null);
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof ApiClientError ? err.message : t("errorGeneric"));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [tripId, reloadKey, t]);

  async function replan() {
    if (busy || !tripId) return;
    setBusy(true);
    try {
      await api.replan(tripId);
      setReloadKey((key) => key + 1);
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : t("errorGeneric"));
    } finally {
      setBusy(false);
    }
  }

  async function share() {
    if (!tripId) return;
    try {
      const link = await api.createShare(tripId);
      const url = `${window.location.origin}/share/${link.token}`;
      await navigator.clipboard?.writeText(url).catch(() => undefined);
      setShareUrl(url);
    } catch {
      setError(t("errorGeneric"));
    }
  }

  return (
    <>
      <Header />
      <main className="mx-auto w-full max-w-4xl flex-1 px-4 py-8">
        {error ? <ErrorBox message={error} /> : null}

        <div className="mb-4 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={replan}
            disabled={busy}
            className="rounded-lg border border-emerald-600 px-4 py-2 text-sm font-semibold text-emerald-700 hover:bg-emerald-50 disabled:opacity-50"
          >
            {busy ? t("replanning") : t("replan")}
          </button>
          <button
            type="button"
            onClick={share}
            className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-900"
          >
            {t("share")}
          </button>
          {shareUrl ? (
            <span className="text-sm text-emerald-700">{t("shareCopied")}</span>
          ) : null}
        </div>

        {payload ? <ItineraryView payload={payload} /> : null}

        {/* Agent trace: structured steps, never chain-of-thought. */}
        <section className="mt-8">
          <h2 className="mb-2 font-bold">{t("traceTitle")}</h2>
          <ul className="space-y-1 text-sm text-slate-600" data-testid="agent-trace">
            {trace.map((item, index) => (
              <li key={index} className="font-mono text-xs">
                {item.created_at.slice(11, 19)} · {item.node} · {item.status}
              </li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-slate-400">
            {localiseDigits(String(trace.length), lang)} steps
          </p>
        </section>
      </main>
    </>
  );
}
