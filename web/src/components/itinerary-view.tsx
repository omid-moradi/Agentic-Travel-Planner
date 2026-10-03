"use client";

import { useMemo, useState } from "react";
import type { ItineraryPayload, DayPlan } from "@/lib/api";
import { formatMoney, localiseDigits } from "@/lib/i18n";
import { useLang } from "@/lib/lang-context";
import { StatusBadge } from "@/components/ui";

/** Day-by-day itinerary: tabs, timeline, budgets, warnings, source drawer. */
export function ItineraryView({ payload }: { payload: ItineraryPayload }) {
  const { lang, t } = useLang();
  const [activeDay, setActiveDay] = useState(1);
  const days = useMemo(() => payload.days ?? [], [payload]);
  const current: DayPlan | undefined = useMemo(
    () => days.find((d) => d.day_number === activeDay) ?? days[0],
    [days, activeDay],
  );

  if (!days.length) {
    return <p className="text-slate-500">{t("unavailable")}</p>;
  }

  return (
    <div>
      {/* Day tabs */}
      <div className="flex flex-wrap gap-2" role="tablist">
        {days.map((day) => (
          <button
            key={day.day_number}
            role="tab"
            aria-selected={day.day_number === activeDay}
            onClick={() => setActiveDay(day.day_number)}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium ${
              day.day_number === activeDay
                ? "bg-emerald-600 text-white"
                : "border border-slate-300 text-slate-600 hover:bg-slate-100"
            }`}
          >
            {t("dayOf")} {localiseDigits(String(day.day_number), lang)} — {day.city}
          </button>
        ))}
      </div>

      {/* Total cost */}
      {payload.total_cost ? (
        <p className="mt-4 text-lg font-semibold" data-testid="total-cost">
          {t("totalCostLabel")}: {formatMoney(payload.total_cost.amount, lang)}{" "}
          <StatusBadge status={payload.total_cost.status} />
        </p>
      ) : null}

      {/* Active day */}
      {current ? (
        <section className="mt-4 rounded-xl border border-slate-200 bg-white p-5">
          <header className="mb-4 flex flex-wrap items-center justify-between gap-2">
            <h2 className="font-bold">
              {t("dayOf")} {localiseDigits(String(current.day_number), lang)} —{" "}
              {current.city} ({current.date})
            </h2>
            {current.daily_budget ? (
              <span className="text-sm text-slate-600">
                {t("budgetLabel")}: {formatMoney(current.daily_budget.amount, lang)}
              </span>
            ) : null}
          </header>

          {current.accommodation ? (
            <p className="mb-3 text-sm text-slate-600">
              🏨 {current.accommodation.name}
            </p>
          ) : null}

          {/* Timeline */}
          <ol className="space-y-3" data-testid="day-activities">
            {current.activities.map((activity, index) => (
              <li
                key={`${activity.place.name}-${index}`}
                className="flex flex-col gap-1 border-s-2 border-emerald-200 ps-4 sm:flex-row sm:items-start sm:gap-4"
              >
                <span className="font-mono text-sm text-emerald-700">
                  {localiseDigits(activity.start_time, lang)}–
                  {localiseDigits(activity.end_time, lang)}
                </span>
                <div className="flex-1">
                  <p className="font-medium">
                    {activity.place.name}{" "}
                    <StatusBadge status={activity.place.status} />
                  </p>
                  {activity.place.description ? (
                    <p className="text-sm text-slate-500">
                      {activity.place.description}
                    </p>
                  ) : null}
                  {activity.place.source ? (
                    <p className="mt-0.5 text-xs text-slate-400">
                      {t("sourcesTitle")}: {activity.place.source.name}
                    </p>
                  ) : null}
                  {activity.transport_to_next ? (
                    <p className="mt-0.5 text-xs text-slate-400">
                      {activity.transport_to_next.mode === "walk"
                        ? "🚶"
                        : "🚕"}{" "}
                      {localiseDigits(
                        activity.transport_to_next.distance_km.toFixed(1),
                        lang,
                      )}{" "}
                      km ·{" "}
                      {localiseDigits(
                        String(activity.transport_to_next.duration_minutes),
                        lang,
                      )}{" "}
                      min
                    </p>
                  ) : null}
                </div>
              </li>
            ))}
          </ol>

          {current.notes.map((note) => (
            <p key={note} className="mt-3 text-sm text-amber-700">
              ⚠ {note}
            </p>
          ))}
        </section>
      ) : null}

      <p className="mt-4 text-xs text-slate-400">{t("estimatedNote")}</p>
    </div>
  );
}
