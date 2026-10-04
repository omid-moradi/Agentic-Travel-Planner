# Evaluation Report

Generated: 2026-10-04T18:25:27.927247+00:00
Mode: offline (mock LLM, curated fixtures)

**25/25 scenarios passed (100.0%)**

Latency (ms): min 58.9, mean 85.3, max 131.6

| Category | Passed | Total |
|---|---|---|
| budget | 3 | 3 |
| edge_case | 3 | 3 |
| incomplete | 5 | 5 |
| international | 3 | 3 |
| iran_domestic | 6 | 6 |
| live_mode | 2 | 2 |
| multi_city | 3 | 3 |

| Scenario | Category | Result | Latency (ms) |
|---|---|---|---|
| tehran_shiraz_3n | iran_domestic | PASS | 125.7 |
| tehran_only_1n | iran_domestic | PASS | 95.5 |
| shiraz_5n_summer | iran_domestic | PASS | 112.9 |
| tehran_winter_week | iran_domestic | PASS | 129.3 |
| shiraz_group_of_8 | iran_domestic | PASS | 110.3 |
| nowruz_peak | iran_domestic | PASS | 119.1 |
| multi_city_5n | multi_city | PASS | 106.5 |
| multi_city_1n_each | multi_city | PASS | 89.1 |
| multi_city_uneven_4n | multi_city | PASS | 79.3 |
| budget_impossible_100 | budget | PASS | 93.0 |
| budget_tight_2m | budget | PASS | 68.9 |
| budget_generous | budget | PASS | 62.8 |
| incomplete_unknown_city | incomplete | PASS | 62.7 |
| incomplete_no_cities | incomplete | PASS | 64.1 |
| incomplete_no_nights | incomplete | PASS | 70.3 |
| incomplete_past_date | incomplete | PASS | 71.8 |
| incomplete_far_future | incomplete | PASS | 74.1 |
| international_paris | international | PASS | 83.2 |
| international_english_output | international | PASS | 76.4 |
| international_mixed_currencies | international | PASS | 62.9 |
| live_mode_rain_reason | live_mode | PASS | 60.6 |
| live_mode_tired_reason | live_mode | PASS | 64.2 |
| edge_long_trip_30n | edge_case | PASS | 131.6 |
| edge_max_travelers | edge_case | PASS | 59.2 |
| edge_one_activity_day | edge_case | PASS | 58.9 |
