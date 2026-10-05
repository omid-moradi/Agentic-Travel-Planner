# Agentic Travel Planner — مرور کامل پروژه

> این سند: فهرست کامل کارهای انجام‌شده + ساختار پروژه با توضیح تک‌تک فایل‌ها.
> مسیر پیش‌رو → `ROADMAP.md` · جمع‌بندی صادقانه → `FINAL-REPORT.md`

**ریپازیتوری:** github.com/omid-moradi/Agentic-Travel-Planner (شاخه `main`)
**وضعیت:** هر ۱۰ فاز کامل، هر فاز با شاخه `phase/N` → merge به `main`، همه گیت‌ها سبز (محلی + CI).

---

## بخش ۱ — کارهای انجام‌شده

### فاز ۰ — ممیزی و طراحی
- ممیزی پروتوتایپ AutoGen + ۹ ADR در `docs/decisions.md` (از جمله: LangGraph به‌جای AutoGen، بهینه‌ساز قطعی، سیاست صداقت، ارجاع بدون رزرو)
- سند معماری و پلان اجرایی ۱۰ فازی (`plan-mode-cline.md`)

### فاز ۱ — زیرساخت پکیج و لایه LLM
- پکیج `src/travel_planner` با نصب editable
- لایه LLM مستقل از پروایدر: `apmix | openai | openai_compatible | ollama | mock`؛ محتوای reasoning در مرز client حذف می‌شود (زنجیره فکر هرگز ذخیره/نمایش داده نمی‌شود)
- `Settings` کاملاً محیطی (بدون شکست import-time) + پروفایل ایران/بین‌الملل (تومان/دلار، تقویم، زبان)
- CLI: `travel-planner config` و `ping`

### فاز ۲ — گراف LangGraph و برنامه‌ریز قطعی
- اسکیماهای Pydantic: `TravelState`، `DataStatus` روی هر فکت (confirmed/estimated/inferred/unavailable)، `Itinerary`، `DayPlan` و غیره
- بهینه‌ساز قطعی (`optimizer/route.py`): haversine، خوشه‌بندی جغرافیایی، nearest-neighbour + 2-opt، سقف بار کاری ۸ ساعت در روز
- گراف LangGraph: ۹ نود research موازی → planner → validator → replan محدود → writer
- CLI: `plan --demo` (تهران→شیراز کاملاً آفلاین)

### فاز ۳ — پروایدرها و اسکرپینگ مسئولانه
- Protocol per قابلیت + `ProviderRegistry` با زنجیره fallback محیطی + CircuitBreaker
- `ScraperClient` مشترک: محافظ SSRF، احترام به robots.txt، rate limit، کش، sanitize حفظ JSON-LD
- پارسر JSON-LD با تست قراردادی در برابر fixture ذخیره‌شده
- پروایدرهای curated + estimator + Open-Meteo و OSRM بدون کلید (تأیید زنده)
- `docs/data-sources.md` + `SOURCES.md`: رجیستری کامل منابع و منابع رد شده با دلیل

### فاز ۴ — API و پایگاه داده
- اسکیمای ۱۶ جدولی SQLAlchemy (SQLite بدون daemon، Postgres در پروداکشن)
- FastAPI زیر `/api/v1`: پاکت خطای یکسان، X-Request-ID، rate limit، CORS
- Endpointهای trips / itinerary (نسخه‌بندی append-only) / messages / trace / replan / share / usage
- حذف کامل `legacy_prototype/` و کد AutoGen

### فاز ۵ — وب فارسی/انگلیسی
- Next.js 16 + TypeScript + Tailwind 4
- i18n fa/en با RTL کامل و ارقام فارسی
- صفحات: landing، new، trips، trips/[id]، share/[token] با نشان‌های provenance
- Playwright golden path (خودش API و وب را بالا می‌آورد)

### فاز ۶ — احراز هویت و درآمدزایی
- PBKDF2 + JWT + نقش‌ها + guest trial (۱ پلن رایگان → پاکت 402)
- `EntitlementService`: سهمیه پلن/re-plan/توکن per tier
- پروایدرهای پرداخت (mock/Stripe/Zarinpal stub) + ماشین حالت اشتراک + webhook idempotent با کلید یکتای (provider, event_id)
- affiliate redirect با افشای کمیسیون اجباری، admin stats

### فاز ۷ — قابلیت‌های سفر
- چک‌لیست بسته‌بندی/مدارک، الزامات ورود advisory با هشدار منبع رسمی
- ردیاب هزینه چندارزی + burn-down، خروجی ICS (RFC 5545) و PDF بدون وابستگی
- Live Mode: `today` + `replan-today` با ۵ دلیل ممیزی‌شده
- PWA: manifest + service worker

### فاز ۸ — مشاهده‌پذیری، ارزیابی، MCP
- Tracer با شکل OTLP + Prometheus در `/api/v1/metrics`
- harness ارزیابی: ۲۵ سناریو، ۲۵/۲۵ = ۱۰۰٪ (گزارش با اعداد واقعی کامیت شده)
- ۱۱ تست failure-injection
- سرور MCP stdio بدون وابستگی (`plan_trip`, `get_health`) — هسته هرگز آن را import نمی‌کند

### فاز ۹ — DevOps، CI، مستندات، گزارش نهایی
- Dockerfile چندمرحله‌ای (non-root، healthcheck، حالت دمو پیش‌فرض) + `web/Dockerfile` (Next.js standalone)
- `docker-compose.yml`: api + web + postgres + redis با health check
- CI در GitHub Actions: ruff، mypy strict، pytest، گیت ارزیابی، pip-audit، web lint/build، Playwright
- ۸ سند جدید + بازنویسی README + `FINAL-REPORT.md`
- داکر راستی‌آزمایی شد: build هر دو ایمیج، استک سالم، ساخت trip واقعی (201)، سهمیه guest (402)، persistence
- CI راستی‌آزمایی شد: run سبز شامل golden path روی لینوکس

### دور اول hardening (باگ‌های واقعی که اجرای Docker/CI کشف کرد)
- نصب wheel با extra `[api]` (fastapi در وابستگی‌های core نبود)
- ساخت/chown دایرکتوری `/app/data` به‌عنوان root قبل از `USER planner`
- `.dockerignore` در ریشه و `web/`
- مسیر compose برای SQLite مطلق و بدون substitution (فایل `.env` لوکال مسیر خراب تزریق می‌کرد)
- دستور Playwright webServer بین‌پلتفرمی + نصب Python در job وب CI
- ساخت `.pytest_tmp` پیش از boot در تست‌های e2e

### دور دوم hardening (رفع مشکلات باقی‌مانده)
- `replan-today` دلیل‌آگاه و فقط روز جاری: tired روز سبک‌تر، rain پیاده‌روی به تاکسی، closed_venue حذف venue، running_late شروع ۲ ساعت دیرتر، budget_changed فقط venueهای ارزان؛ سایر روزها دست‌نخورده
- چرخش venue در یک شهر: لنگر مسیر per روز می‌چرخد → روزهای متوالی تکراری نیستند
- باگ پنهان سقف ۸ ساعت: projection داخلی planner دقایق سفر را نمی‌شمرد ولی validator می‌شمرد (evaluation افت کرد به ۲۲/۲۵ و گیت دقیقاً کارش را کرد) → اصلاح شد
- جدول `user_credentials`: هش پسورد از JSON preferences به جدول اختصاصی + مهاجرت تنبل هش‌های فاز ۶ در اولین login
- تست آفلاین SW: `setOffline(true)` + reload → صفحه از کش service worker بالا می‌آید (آیتم PWA به «تأییدشده» منتقل شد)

### اعداد نهایی گیت‌ها

| گیت | نتیجه |
|---|---|
| ruff + mypy strict (۷۰ فایل) | پاک |
| تست آفلاین | ۲۲۵ پاس |
| ارزیابی | ۲۵/۲۵ (۱۰۰٪) |
| تست زنده (اختیاری) | ۱۲ پاس (apmix، Open-Meteo، OSRM) |
| Playwright | ۲/۲ (golden path + آفلاین) |
| Docker stack | راستی‌آزمایی‌شده |
| CI GitHub Actions | سبز (هر دو job) |

---
## بخش ۲ — ساختار پروژه و توضیح هر فایل

### ریشه پروژه

| فایل | کار |
|---|---|
| `README.md` | نقطه ورود محصول: ویژگی‌ها، ۴ متمایزکننده، quick start، Docker، تست‌ها، envها، roadmap |
| `FINAL-REPORT.md` | گزارش نهایی صادقانه: تأییدشده/تأییدنشده، محدودیت‌ها، دستورات دقیق، چک‌لیست عرضه |
| `PROJECT-OVERVIEW.md` | همین سند — مرور کارها + نقشه کامل فایل‌ها |
| `ROADMAP.md` | مسیر پیش‌رو با چک‌باکس‌های تیک‌خوردنی |
| `plan-mode-cline.md` | پلان اجرایی گیت‌دار ۱۰ فازی (سند برنامه‌ریزی اصلی) |
| `STATUS-P0.md` … `STATUS-P9.md` | گزارش صادقانه هر فاز: انجام‌شده، راستی‌آزمایی‌شده، محدودیت‌ها |
| `SOURCES.md` | خلاصه منابع داده و وضعیت مجوز/اسکرپ هر کدام |
| `pyproject.toml` | تعریف پکیج، وابستگی‌ها و extraها، تنظیم ruff/mypy/pytest |
| `requirements.txt` | پین وابستگی‌ها برای محیط‌های بدون pyproject |
| `.env.example` | نمونه متغیرهای محیطی (بدون هیچ مقدار واقعی) |
| `.env` | مقادیر واقعی — git-ignored، هرگز کامیت نمی‌شود |
| `.gitignore` | قواعد نادیده‌گرفتن (env، دیتابیس‌ها، کش‌ها) |
| `.pre-commit-config.yaml` | قلاب‌های pre-commit از جمله اسکن رازها |
| `.dockerignore` | نگه‌داشتن context بیلد داکر مینیمال و پاک |
| `Dockerfile` | ایمیج API: بیلد wheel → runtime لاغم، non-root، healthcheck، دمو پیش‌فرض |
| `docker-compose.yml` | کل استک: api + web + postgres + redis با health check و گارد JWT_SECRET |
| `.github/workflows/ci.yml` | CI: job پایتون (ruff/mypy/pytest/eval/pip-audit) + job وب (lint/build/Playwright) |
| `scripts/check_no_secrets.py` | قلاب جلوگیری از کامیت کلیدها و رازهای واقعی |

---

### `src/travel_planner/` — هسته بک‌اند (۷۱ فایل)

#### ریشه پکیج
| فایل | کار |
|---|---|
| `__init__.py` | نشانه‌گذاری پکیج + فراداده نسخه |
| `errors.py` | سلسله خطاهای دامنه (`TravelPlannerError`، `ScrapingNotPermittedError` و…) |
| `logging_config.py` | لاگ ساختاریافته با redact کردن رازها و PII |
| `cli.py` | خط فرمان: `plan` (شامل `--demo`)، `config`، `ping` |
| `py.typed` | نشانه پشتیبانی کامل typing برای مصرف‌کنندگان |

#### `config/`
| فایل | کار |
|---|---|
| `settings.py` | `Settings` کاملاً env-driven (بازloadable برای تست‌ها)، JWT، سهمیه‌ها، زنجیره پروایدرها |
| `regions.py` | پروفایل `RegionProfile`: ایران/بین‌الملل — ارز، تقویم، زبان، گردش کار |

#### `llm/`
| فایل | کار |
|---|---|
| `factory.py` | لایه LLM مستقل از پروایدر: apmix/openai/ollama/mock، حذف reasoning_content، JSON mode، tool calls |

#### `schemas/`
| فایل | کار |
|---|---|
| `__init__.py` | تمام مدل‌های Pydantic: `TravelState`، `Finding`، `PlaceInfo`، `DayPlan`، `Itinerary`، `DataStatus` و… |

#### `optimizer/`
| فایل | کار |
|---|---|
| `route.py` | بهینه‌ساز قطعی: haversine، خوشه‌بندی، nearest-neighbour + 2-opt، سقف ۸ ساعت |

#### `graph/` — گردش کار LangGraph
| فایل | کار |
|---|---|
| `build.py` | ساخت گراف: ۹ research موازی → planner → validator → replan محدود → writer |
| `nodes/research.py` | ۹ نود research با fixtureهای شهر + provenance روی هر finding |
| `nodes/planner.py` | برنامه‌ریز قطعی: توزیع روزها بین شهرها، چرخش لنگر مسیر per روز، زمان‌بندی، سقف بار کاری، بودجه تومان |
| `nodes/validator.py` | اعتبارسنج کدخالص: ترتیب، تکرار، تاریخ‌ها، سقف کاری، بودجه — بدون LLM |
| `nodes/writer.py` | خروجی فارسی/انگلیسی با برچسب اطمینان و اعلان «قیمت‌ها ممکن است فرق کند» |

#### `data/fixtures/`
| فایل | کار |
|---|---|
| `iran.py` | داده curated تهران/شیراز: venueها، هتل‌ها، رستوران‌ها، مختصات، ساعات کاری، `estimated_price` |

#### `providers/` — زنجیره پروایدرها
| فایل | کار |
|---|---|
| `base.py` | Protocolهای هر قابلیت + مدل‌های نتیجه |
| `registry_factory.py` | `ProviderRegistry` محیطی با fallback + CircuitBreaker |
| `http/scraper_client.py` | fetch مشترک: SSRF، robots.txt، rate limit، کش، sanitize، فیلتر تزریق پرامپت |
| `http/jsonld.py` | پارسر JSON-LD از HTML (تست قراردادی در برابر fixture) |
| `places/curated_places.py` | پروایدر مکان‌های curated |
| `places/scraper_jsonld.py` | اسکرپر جاذبه‌ها از JSON-LD (تا تأیید مالک فعال نیست) |
| `hotels/curated_hotels.py` | هتل‌های curated با نرخ برچسب‌خورده estimated |
| `transport/` + `ride_fare/estimator.py` | حمل‌ونقل curated/برآوردی (جفت‌شهر ناشناخته را رد می‌کند، جعل نمی‌کند)؛ کرکه اسنپ/تپسی فرمولی و برچسب‌دار |
| `weather/open_meteo.py` | Open-Meteo بدون کلید؛ فراتر از پنجره پیش‌بینی → unavailable صادقانه |
| `routes/osrm.py` | مسیر OSRM (قابل self-host با `OSRM_BASE_URL`) |

#### `db/`
| فایل | کار |
|---|---|
| `models.py` | ۱۶ جدول SQLAlchemy: کاربران، `user_credentials`، اشتراک، usage، tripها، پیام‌ها، itinerary نسخه‌بندی‌شده، agent trace، share، affiliate، webhook، هزینه‌ها |
| `session.py` | موتور async lazy per-URL، ساخت اسکیمای هنگام startup، پشتیبانی SQLite/Postgres |

#### `api/` — FastAPI
| فایل | کار |
|---|---|
| `app.py` | ساخت اپ: میدل‌ور خطا/X-Request-ID، rate limit، CORS، اتصال routerها |
| `routers/trips.py` | CRUD سفر + itinerary + replan + messages + trace |
| `routers/whole_trip.py` | چک‌لیست، مدارک ورود، هزینه‌ها، خروجی ICS/PDF، Live Mode (`today`، `replan-today` دلیل‌آگاه فقط برای امروز) |
| `routers/auth.py` | ثبت‌نام/ورود/me با JWT |
| `routers/billing.py` | checkout، وضعیت اشتراک، webhook idempotent |
| `routers/affiliate.py` | ثبت کلیک + ریدایرکت با افشای کمیسیون |
| `routers/admin.py` | آمار ادمین با کنترل نقش |
| `routers/share.py` | صفحه عمومی فقط‌خواندنی با توکن |
| `routers/usage.py` | مصرف کاربر (پلن، سهمیه، توکن) |
| `routers/health.py` | health/ready |
| `routers/observability.py` | Prometheus metrics |

#### `services/` — منطق دامنه
| فایل | کار |
|---|---|
| `trips.py` | اجرای گراف per سفر + ذخیره نسخه append-only itinerary + trace |
| `auth.py` | PBKDF2 + JWT + جدول credential + مهاجرت تنبل legacy |
| `entitlements.py` | سهمیه guest/free/pro/team (پلن، re-plan، توکن) از usage_events |
| `payments.py` | پروتکل پرداخت: mock/Stripe/Zarinpal + ماشین حالت اشتراک + webhook idempotent |
| `affiliate.py` | ثبت کلیک و افشای کمیسیون |
| `checklists.py` | چک‌لیست بسته‌بندی/مدارک با هشدار منبع رسمی |
| `entry_requirements.py` | الزامات ورود advisory با هشدار اجباری |
| `expenses.py` | ثبت هزینه چندارزی با تبدیل ایستا + burn-down |
| `exports.py` | خروجی ICS (RFC 5545) و PDF تک‌صفحه‌ای بدون وابستگی |
| `live_mode.py` | برنامه امروز + next_stop + تبدیل‌های دلیل‌آگاه (`apply_reason`، `merge_patched_today`) |

#### `observability/` و `mcp/`
| فایل | کار |
|---|---|
| `observability/__init__.py` | Tracer شکل OTLP + شمارنده‌های Prometheus |
| `mcp/server.py` | سرور MCP stdio بدون وابستگی: `plan_trip`، `get_health` (هسته هرگز importش نمی‌کند) |

---

### `web/` — فرانت‌اند (۳۷ فایل)

| فایل | کار |
|---|---|
| `Dockerfile` | ایمیج Next.js standalone (بیلد → فایل‌های prod لاغم) |
| `.dockerignore` | جلوگیری از ورود node_modules/next هاست به ایمیج |
| `package.json` / `package-lock.json` | وابستگی‌ها و اسکریپت‌ها (dev/build/start/lint) با pin کامل |
| `next.config.ts` | فعال‌سازی `output: standalone` برای داکر |
| `tsconfig.json` / `eslint.config.mjs` / `postcss.config.mjs` | تنظیمات TypeScript (strict)، ESLint، Tailwind |
| `playwright.config.ts` | boot خودکار API (بین‌پلتفرمی، ساخت دایرکتوری db) + وب توسط Playwright |
| `e2e/golden-path.spec.ts` | تست مسیر طلایی: ساخت سفر → بازسازی → اشتراک‌گذاری |
| `e2e/offline.spec.ts` | تست آفلاین PWA: قطع شبکه → صفحه از کش SW بالا می‌آید |
| `src/app/layout.tsx` | ریشه RTL/fa، فونت‌ها، ثبت service worker |
| `src/app/page.tsx` | صفحه فرود با i18n و RTL |
| `src/app/new/page.tsx` | فرم درخواست سفر و ساخت برنامه |
| `src/app/trips/page.tsx` | فهرست سفرهای من |
| `src/app/trips/[id]/page.tsx` | صفحه سفر: تب روزها، فعالیت‌ها، بازسازی، اشتراک |
| `src/app/share/[token]/page.tsx` | نمای عمومی فقط‌خواندنی |
| `src/components/itinerary-view.tsx` | نمایش itinerary با نشان‌های provenance و ارقام فارسی |
| `src/components/ui.tsx` | اجزای پایه UI |
| `src/components/sw-registrar.tsx` | ثبت service worker (خطا هرگز صفحه را نمی‌شکند) |
| `src/lib/i18n.ts` | دیکشنری fa/en + قالب‌بندی اعداد/تاریخ |
| `src/lib/api.ts` | کلاینت fetch API با URL محیطی |
| `src/lib/lang-context.tsx` | کانتکست زبان/جهت |
| `public/manifest.json` | مانیفست PWA |
| `public/sw.js` | service worker: کش cache-first برای GET ها |
| `public/icon.svg` | آیکون برنامه |
| `AGENTS.md` / `CLAUDE.md` / `README.md` | راهنمای عامل‌های کدنویسی در پوشه وب |

---

### `tests/` — ۲۲۵ تست آفلاین + ۱۲ زنده

| فایل | کار |
|---|---|
| `unit/test_schemas.py` | اعتبارسنجی اسکیماها و DataStatus |
| `unit/test_optimizer.py` | haversine، خوشه‌بندی، 2-opt، سقف بار کاری، چرخش لنگر |
| `unit/test_llm_factory.py` | هر پروایدر LLM + حذف reasoning + JSON mode + tool calls |
| `unit/test_config.py` | Settings محیطی و reload |
| `unit/test_logging.py` | redact رازها، idempotent بودن پیکربندی |
| `unit/test_cli.py` | دستورات CLI شامل دمو آفلاین |
| `unit/test_providers.py` | زنجیره registry، fallback، circuit breaker |
| `unit/test_scraper_client.py` | SSRF، robots، rate limit، sanitize، کش (۲۶ تست) |
| `unit/test_mcp.py` | round-trip سرور MCP |
| `unit/test_live_mode.py` | تبدیل‌های دلیل‌آگاه `apply_reason` + merge فقط-امروز |
| `unit/test_auth_credentials.py` | جدول credential + مهاجرت تنبل legacy |
| `integration/test_graph.py` | اجرای کامل گراف offline: ۹ research → plan → validate → write |
| `integration/test_api.py` | API e2e: ساخت/لیست/replan/trace/سهمیه/اشتراک |
| `integration/test_monetization.py` | ثبت‌نام/ورود، سهمیه tier، webhook idempotent، ادمین |
| `integration/test_whole_trip.py` | چک‌لیست، مدارک، هزینه، خروجی‌ها، Live Mode + patch فقط-امروز |
| `integration/test_failure_injection.py` | ۱۱ سناریوی شکست: پایگاه داده، پروایدر، LLM، webhook |
| `integration/test_live_llm.py` | ۱۲ گیت زنده apmix (chat/tools/JSON/حذف reasoning) — needs key |
| `integration/test_live_providers.py` | Open-Meteo و OSRM زنده (بدون کلید) |
| `fixtures/html/attractions_shiraz.html` | fixture قراردادی پارسر JSON-LD |

### `evaluation/` — harness ارزیابی (گیت فاز ۸)

| فایل | کار |
|---|---|
| `scenarios.py` | ۲۵ سناریو در ۷ دسته (ایران، چندشهری، بودجه، ناقص، بین‌الملل، Live Mode، لبه) |
| `runner.py` | اجرا + متریک‌ها (اعتبار، روزها، پوشش شهر، سقف، بودجه، latency) |
| `reports/evaluation-report.{json,md}` | آخرین نتیجه کامیت‌شده: ۲۵/۲۵ = ۱۰۰٪ |

### `docs/` — مستندات

| فایل | کار |
|---|---|
| `architecture.md` | معماری کل سیستم |
| `agents.md` | نودهای گراف و قواعد عامل‌ها |
| `tools.md` | قابلیت‌های پروایدر + سرور MCP |
| `api.md` | مرجع کامل endpointها |
| `data-sources.md` | رجیستری منابع + قواعد اسکرپ مسئولانه + منابع رد شده |
| `deployment.md` | اجرای محلی/داکر/پروداکشن |
| `evaluation.md` | روش ارزیابی + آخرین اعداد |
| `security.md` | وضعیت امنیتی پیاده‌شده و موارد نیازمند بازبینی حقوقی |
| `monetization.md` | درآمدزایی: trial، tierها، پرداخت، affiliate |
| `iran-mode.md` | جزئیات حالت ایران: تقویم، تومان، اتصال |
| `decisions.md` | ۹ ADR |
| `audit.md` | ممیزی اولیه فاز ۰ |
