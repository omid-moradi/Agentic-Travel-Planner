"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ErrorBox, Header } from "@/components/ui";
import { api, ApiClientError, type TripSummary } from "@/lib/api";
import { localiseDigits } from "@/lib/i18n";
import { useLang } from "@/lib/lang-context";

export default function TripsPage() {
  const { lang, t } = useLang();
  const [trips, setTrips] = useState<TripSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .listTrips()
      .then((response) => setTrips(response.items))
      .catch((err) =>
        setError(err instanceof ApiClientError ? err.message : t("errorGeneric")),
      )
      .finally(() => setLoading(false));
  }, [t]);

  return (
    <>
      <Header />
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-8">
        <h1 className="text-2xl font-bold">{t("myTrips")}</h1>

        {loading ? <p className="mt-4 text-slate-500">…</p> : null}
        {error ? (
          <div className="mt-4">
            <ErrorBox message={error} />
          </div>
        ) : null}

        {!loading && !error && trips.length === 0 ? (
          <p className="mt-4 text-slate-500">{t("noTrips")}</p>
        ) : null}

        <ul className="mt-6 space-y-3">
          {trips.map((trip) => (
            <li key={trip.id}>
              <Link
                href={`/trips/${trip.id}`}
                className="block rounded-xl border border-slate-200 bg-white p-4 hover:border-emerald-400"
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="font-semibold">{trip.title}</span>
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs ${
                      trip.status === "done"
                        ? "bg-emerald-100 text-emerald-800"
                        : trip.status === "failed"
                          ? "bg-red-100 text-red-700"
                          : "bg-amber-100 text-amber-800"
                    }`}
                  >
                    {trip.status === "done"
                      ? t("statusDone")
                      : trip.status === "failed"
                        ? t("statusFailed")
                        : t("statusPlanning")}
                  </span>
                </div>
                <p className="mt-1 text-sm text-slate-500">
                  {localiseDigits(String(trip.duration_nights), lang)}{" "}
                  {t("nights")} · {localiseDigits(String(trip.travelers), lang)}{" "}
                  {t("travelers")}
                </p>
              </Link>
            </li>
          ))}
        </ul>
      </main>
    </>
  );
}
