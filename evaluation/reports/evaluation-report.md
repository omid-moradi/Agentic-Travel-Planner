# Evaluation Report

Generated: 2026-10-04T21:43:13.856160+00:00
Mode: offline (mock LLM, curated fixtures)

**25/25 scenarios passed (100.0%)**

Latency (ms): min 62.1, mean 74.6, max 120.0

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
| tehran_shiraz_3n | iran_domestic | PASS | 74.7 |
| tehran_only_1n | iran_domestic | PASS | 64.9 |
| shiraz_5n_summer | iran_domestic | PASS | 70.1 |
| tehran_winter_week | iran_domestic | PASS | 78.2 |
| shiraz_group_of_8 | iran_domestic | PASS | 67.1 |
| nowruz_peak | iran_domestic | PASS | 71.6 |
| multi_city_5n | multi_city | PASS | 82.6 |
| multi_city_1n_each | multi_city | PASS | 71.8 |
| multi_city_uneven_4n | multi_city | PASS | 82.2 |
| budget_impossible_100 | budget | PASS | 84.8 |
| budget_tight_2m | budget | PASS | 86.6 |
| budget_generous | budget | PASS | 67.8 |
| incomplete_unknown_city | incomplete | PASS | 71.2 |
| incomplete_no_cities | incomplete | PASS | 62.1 |
| incomplete_no_nights | incomplete | PASS | 79.0 |
| incomplete_past_date | incomplete | PASS | 89.1 |
| incomplete_far_future | incomplete | PASS | 73.7 |
| international_paris | international | PASS | 67.1 |
| international_english_output | international | PASS | 66.1 |
| international_mixed_currencies | international | PASS | 71.6 |
| live_mode_rain_reason | live_mode | PASS | 62.8 |
| live_mode_tired_reason | live_mode | PASS | 64.8 |
| edge_long_trip_30n | edge_case | PASS | 120.0 |
| edge_max_travelers | edge_case | PASS | 67.5 |
| edge_one_activity_day | edge_case | PASS | 66.9 |
