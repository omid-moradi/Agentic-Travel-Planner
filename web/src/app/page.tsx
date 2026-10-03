"use client";

import Link from "next/link";
import { Header } from "@/components/ui";
import { FEATURES } from "@/lib/i18n";
import { useLang } from "@/lib/lang-context";

export default function LandingPage() {
  const { lang, t } = useLang();
  const features = FEATURES[lang];

  return (
    <>
      <Header />
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-10">
        <section className="text-center">
          <p className="mb-2 font-medium text-emerald-700">{t("tagline")}</p>
          <h1 className="mx-auto max-w-2xl text-4xl font-bold leading-tight">
            {t("heroTitle")}
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-slate-600">{t("heroBody")}</p>
          <div className="mt-6 flex justify-center gap-3">
            <Link
              href="/new"
              className="rounded-lg bg-emerald-600 px-5 py-2.5 font-semibold text-white hover:bg-emerald-700"
            >
              {t("ctaNewTrip")}
            </Link>
            <Link
              href="/trips"
              className="rounded-lg border border-slate-300 px-5 py-2.5 font-semibold text-slate-700 hover:bg-slate-100"
            >
              {t("myTrips")}
            </Link>
          </div>
        </section>

        <section className="mt-12 grid gap-4 sm:grid-cols-2">
          {features.map((feature) => (
            <article
              key={feature.title}
              className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
            >
              <h2 className="font-semibold text-slate-900">{feature.title}</h2>
              <p className="mt-2 text-sm text-slate-600">{feature.body}</p>
            </article>
          ))}
        </section>

        <p className="mt-10 text-center text-xs text-slate-400">
          {t("estimatedNote")}
        </p>
      </main>
    </>
  );
}
