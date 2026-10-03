"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { ErrorBox, Header, PlanningIndicator } from "@/components/ui";
import { api, ApiClientError } from "@/lib/api";
import { useLang } from "@/lib/lang-context";

export default function NewTripPage() {
  const { t } = useLang();
  const router = useRouter();
  const [request, setRequest] = useState("");
  const [nights, setNights] = useState(3);
  const [travelers, setTravelers] = useState(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!request.trim() || busy) return;
    setBusy(true);
    setError(null);
    try {
      const trip = await api.createTrip({
        request: request.trim(),
        duration_nights: nights,
        travelers,
      });
      router.push(`/trips/${trip.id}`);
    } catch (err) {
      setError(
        err instanceof ApiClientError ? err.message : t("errorGeneric"),
      );
      setBusy(false);
    }
  }

  return (
    <>
      <Header />
      <main className="mx-auto w-full max-w-2xl flex-1 px-4 py-10">
        <h1 className="text-2xl font-bold">{t("formTitle")}</h1>

        <form onSubmit={submit} className="mt-6 space-y-4" aria-busy={busy}>
          <textarea
            value={request}
            onChange={(e) => setRequest(e.target.value)}
            placeholder={t("formPlaceholder")}
            rows={4}
            required
            minLength={3}
            maxLength={4000}
            className="w-full rounded-xl border border-slate-300 p-4 focus:border-emerald-500 focus:outline-none"
            aria-label={t("formTitle")}
          />

          <div className="grid grid-cols-2 gap-4">
            <label className="block text-sm">
              <span className="mb-1 block font-medium">{t("nights")}</span>
              <input
                type="number"
                min={1}
                max={90}
                value={nights}
                onChange={(e) => setNights(Number(e.target.value))}
                className="w-full rounded-lg border border-slate-300 px-3 py-2"
              />
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-medium">{t("travelers")}</span>
              <input
                type="number"
                min={1}
                max={50}
                value={travelers}
                onChange={(e) => setTravelers(Number(e.target.value))}
                className="w-full rounded-lg border border-slate-300 px-3 py-2"
              />
            </label>
          </div>

          {error ? <ErrorBox message={error} /> : null}

          <div className="flex items-center gap-4">
            <button
              type="submit"
              disabled={busy || request.trim().length < 3}
              className="rounded-lg bg-emerald-600 px-6 py-2.5 font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
            >
              {t("submitPlan")}
            </button>
            {busy ? <PlanningIndicator label={t("planning")} /> : null}
          </div>

          {busy ? (
            <p className="text-sm text-slate-500">{t("planningBody")}</p>
          ) : null}
        </form>
      </main>
    </>
  );
}
