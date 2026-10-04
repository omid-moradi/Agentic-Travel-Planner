# Evaluation Report

Generated: 2026-10-04T16:48:01.287737+00:00
Mode: offline (mock LLM, curated fixtures)

**25/25 scenarios passed (100.0%)**

Latency (ms): min 56.7, mean 70.5, max 112.4

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
| tehran_shiraz_3n | iran_domestic | PASS | 84.4 |
| tehran_only_1n | iran_domestic | PASS | 68.5 |
| shiraz_5n_summer | iran_domestic | PASS | 71.4 |
| tehran_winter_week | iran_domestic | PASS | 76.5 |
| shiraz_group_of_8 | iran_domestic | PASS | 67.5 |
| nowruz_peak | iran_domestic | PASS | 68.4 |
| multi_city_5n | multi_city | PASS | 70.8 |
| multi_city_1n_each | multi_city | PASS | 68.6 |
| multi_city_uneven_4n | multi_city | PASS | 65.0 |
| budget_impossible_100 | budget | PASS | 63.2 |
| budget_tight_2m | budget | PASS | 65.2 |
| budget_generous | budget | PASS | 63.8 |
| incomplete_unknown_city | incomplete | PASS | 65.7 |
| incomplete_no_cities | incomplete | PASS | 63.9 |
| incomplete_no_nights | incomplete | PASS | 72.8 |
| incomplete_past_date | incomplete | PASS | 66.2 |
| incomplete_far_future | incomplete | PASS | 88.8 |
| international_paris | international | PASS | 79.4 |
| international_english_output | international | PASS | 68.3 |
| international_mixed_currencies | international | PASS | 73.2 |
| live_mode_rain_reason | live_mode | PASS | 64.1 |
| live_mode_tired_reason | live_mode | PASS | 60.8 |
| edge_long_trip_30n | edge_case | PASS | 112.4 |
| edge_max_travelers | edge_case | PASS | 57.2 |
| edge_one_activity_day | edge_case | PASS | 56.7 |
