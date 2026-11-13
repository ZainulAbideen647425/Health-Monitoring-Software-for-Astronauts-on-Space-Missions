# Machine-learning analytics

Endpoint: `GET /astronauts/{id}/health-analytics` (same sign-in and role rules as other health data). Shown on the dashboard under **Health intelligence > Model flags**, and forecasts also appear in **Attention & reminders**.

Libraries: scikit-learn, pandas, NumPy. Code: `domain/health_analytics.py` (models) and `services/health_analytics_service.py`.

## 1. Unusual-day detection (anomaly detection)
- Readings are averaged per day and arranged as a table (one row per day, one column per indicator) with pandas.
- Values are standardised, then an **Isolation Forest** (200 trees, fixed random seed so results repeat) scores each day.
- A day is flagged when its **combination** of values is rare for this astronaut, even if every single value is inside its normal range. The indicators that differ most are listed as the reason.
- Needs at least 10 days and 2 indicators with enough history; otherwise nothing is flagged.

## 2. Three-day risk forecast
- For each indicator with at least 7 days, a **linear regression** is fitted to the daily means and projected 3 days ahead.
- A risk is raised only if the fit is reasonable (R squared at least 0.3) **and** the fitted line has moved at least the indicator's "meaningful change". Noise is ignored.
- `watch`: projected value leaves the healthy range. `high`: it reaches the critical limit. Otherwise `none`.

## Safety design
- Models only **flag for human review**. The rule-based status (with sourced ranges) stays the safety-critical judgement and always wins.
- Each astronaut's models use only that astronaut's data ("unusual" means unusual for this person).
- Output wording never says diagnosis; the API includes a `method` string and the dashboard repeats it.

## Honest limits
- Small models on short histories (days, not months). They are not clinically validated.
- Linear trends cannot see sudden or cyclic changes. Isolation Forest flags a fixed share of unusual-looking days even on healthy data, so a flag means "have a look", not "something is wrong".
- No pre-trained model on real spaceflight data was used, because no suitable open dataset was bundled.

Tests: `tests/unit/test_health_analytics.py` and `tests/integration/test_health_analytics_api.py`.
