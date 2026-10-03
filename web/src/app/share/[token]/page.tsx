"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ErrorBox, Header } from "@/components/ui";
import { ItineraryView } from "@/components/itinerary-view";
import { api, ApiClientError, type SharedTrip } from "@/lib/api";
import { useLang } from "@/lib/lang-context";

/** The public, read-only trip page. No edit actions exist here by design. */
export default function SharedTripPage() {
  const { t } = useLang();
  const params = useParams<{ token: string }>();
  const token = params?.token ?? "";
  const [shared, setShared] = useState<SharedTrip | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    api
      .getShared(token)
      .then(setShared)
      .catch((err) =>
        setError(err instanceof ApiClientError ? err.message : t("errorGeneric")),
      );
  }, [token, t]);

  return (
    <>
      <Header />
      <main className="mx-auto w-full max-w-4xl flex-1 px-4 py-8">
        {error ? <ErrorBox message={error} /> : null}

        {shared ? (
          <>
            <header className="mb-6">
              <p className="text-sm font-medium text-slate-500">
                {t("sharedTitle")}
              </p>
              <h1 className="text-2xl font-bold">{shared.trip.title}</h1>
            </header>

            {shared.itinerary ? (
              <ItineraryView payload={shared.itinerary.payload} />
            ) : (
              <p className="text-slate-500">{t("unavailable")}</p>
            )}
          </>
        ) : !error ? (
          <p className="text-slate-500">…</p>
        ) : null}
      </main>
    </>
  );
}
