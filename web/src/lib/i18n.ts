/**
 * Minimal i18n: two dictionaries (fa, en), full RTL, Persian digits.
 * Kept dependency-free on purpose - the product has exactly two locales
 * and a compile-time-known key set.
 */

export type Lang = "fa" | "en";

export const LANGS: Lang[] = ["fa", "en"];

export const DIRS: Record<Lang, "rtl" | "ltr"> = { fa: "rtl", en: "ltr" };

const fa = {
  appName: "دستیار سفر هوشمند",
  tagline: "برنامهٔ کامل سفر — از تحقیق تا اجرا",
  heroTitle: "سفر بعدی‌ات را در چند ثانیه برنامه‌ریزی کن",
  heroBody:
    "برنامهٔ روزبه‌روز با مسیر بهینه، بودجهٔ شفاف و منابع قابل استناد — برای سفرهای داخلی ایران و خارج از کشور، به فارسی و انگلیسی.",
  ctaNewTrip: "برنامه‌ریزی سفر جدید",
  ctaMyTrips: "سفرهای من",
  formTitle: "سفرت رو تو بگو",
  formPlaceholder: "مثلاً: سه شب تهران و شیراز، فرهنگی، دو نفره",
  nights: "تعداد شب",
  travelers: "مسافران",
  language: "زبان خروجی",
  submitPlan: "برنامه بساز",
  planning: "در حال برنامه‌ریزی…",
  planningBody: "عامل‌ها در حال تحقیق و بهینه‌سازی مسیر هستند. چند لحظه صبر کن.",
  statusDone: "آماده",
  statusPlanning: "در حال ساخت",
  statusFailed: "ناموفق",
  dayOf: "روز",
  budgetLabel: "بودجهٔ روز",
  totalCostLabel: "هزینهٔ کل (تقریبی)",
  estimatedNote: "قیمت‌ها تقریبی هستند و ممکن است در سایت ارائه‌دهنده متفاوت باشند.",
  sourcesTitle: "منابع",
  confirmed: "تأییدشده",
  estimated: "تقریبی",
  inferred: "استنباطی",
  unavailable: "در دسترس نیست",
  myTrips: "سفرهای من",
  noTrips: "هنوز سفری نساخته‌ای.",
  traceTitle: "ردپای عامل‌ها",
  replan: "بازسازی برنامه",
  replanning: "در حال بازسازی…",
  share: "لینک اشتراک بساز",
  shareCopied: "لینک کپی شد",
  sharedTitle: "سفر اشتراکی (فقط‌خواندنی)",
  backHome: "بازگشت",
  errorGeneric: "خطایی رخ داد. دوباره تلاش کن.",
  tripNotFound: "سفر پیدا نشد.",
} as const;

export type Feature = { title: string; body: string };

/** Feature cards, per locale (kept out of the flat dictionary on purpose). */
export const FEATURES: Record<Lang, readonly Feature[]> = {
  fa: [
    {
      title: "واقعیت‌های مستند",
      body: "هر اطلاعات یک منبع و برچسب اطمینان دارد: تأییدشده، تقریبی، استنباطی یا در دسترس نیست.",
    },
    {
      title: "بهینه‌سازی قطعی",
      body: "مسیرها، ساعات کاری و بودجه با الگوریتم محاسبه می‌شوند، نه حدس مدل.",
    },
    {
      title: "ویرایش گفتگویی",
      body: "«ارزان‌تر»، «موزه‌ها را حذف کن» یا «یک روز اضافه کن» — فقط بخش‌های آسیب‌دیده بازسازی می‌شوند.",
    },
    {
      title: "ردپای شفاف عامل‌ها",
      body: "مراحل ساختاریافته و زمان‌بندی؛ هرگز زنجیرهٔ استدلال مدل نمایش داده نمی‌شود.",
    },
  ],
  en: [
    {
      title: "Sourced facts",
      body: "Every fact carries a source and a confidence label: confirmed, estimated, inferred or unavailable.",
    },
    {
      title: "Deterministic optimization",
      body: "Routes, opening hours and budgets are computed by an algorithm, not guessed by a model.",
    },
    {
      title: "Conversational edits",
      body: '"cheaper", "remove museums" or "add a day" - only the affected parts are re-planned.',
    },
    {
      title: "Transparent agent trace",
      body: "Structured steps and timings; the model chain-of-thought is never shown.",
    },
  ],
};

export type DictKey = keyof typeof fa;

const en: Record<DictKey, string> = {
  appName: "Smart Travel Assistant",
  tagline: "The whole trip - from research to execution",
  heroTitle: "Plan your next trip in seconds",
  heroBody:
    "A day-by-day plan with optimized routes, a transparent budget and sourced facts - for domestic Iran and international trips, in Persian and English.",
  ctaNewTrip: "Plan a new trip",
  ctaMyTrips: "My trips",
  formTitle: "Tell us about your trip",
  formPlaceholder: "e.g. 3 nights in Tehran and Shiraz, cultural, 2 travelers",
  nights: "Nights",
  travelers: "Travelers",
  language: "Output language",
  submitPlan: "Build the plan",
  planning: "Planning…",
  planningBody: "The agents are researching and optimizing the route. One moment.",
  statusDone: "Ready",
  statusPlanning: "Building",
  statusFailed: "Failed",
  dayOf: "Day",
  budgetLabel: "Daily budget",
  totalCostLabel: "Estimated total",
  estimatedNote: "Prices are estimates and may differ on the provider's site.",
  sourcesTitle: "Sources",
  confirmed: "confirmed",
  estimated: "estimated",
  inferred: "inferred",
  unavailable: "unavailable",
  myTrips: "My trips",
  noTrips: "No trips yet.",
  traceTitle: "Agent trace",
  replan: "Re-plan",
  replanning: "Re-planning…",
  share: "Create share link",
  shareCopied: "Link copied",
  sharedTitle: "Shared trip (read-only)",
  backHome: "Back",
  errorGeneric: "Something went wrong. Try again.",
  tripNotFound: "Trip not found.",
};

export const DICTS: Record<Lang, Record<DictKey, string>> = { fa, en };

/** Persian digits for the fa locale. */
export function localiseDigits(text: string, lang: Lang): string {
  if (lang !== "fa") return text;
  const faDigits = "۰۱۲۳۴۵۶۷۸۹";
  return text.replace(/[0-9]/g, (d) => faDigits[Number(d)]);
}

export function formatMoney(amount: number | null | undefined, lang: Lang): string {
  if (amount === null || amount === undefined) return "-";
  const grouped = new Intl.NumberFormat("en-US").format(amount);
  const suffix = lang === "fa" ? "تومان" : "Toman";
  return `${localiseDigits(grouped, lang)} ${suffix}`;
}
