# Spaceflight context, environments, schedule and routine

## Hazards and indicators
`GET /spaceflight-context` (sign-in required) returns, for every indicator: which of NASA's five hazards change it, how they change it, why it needs checking, how it is measured on board, a suggested interval, and a source link.
Hazard names follow NASA's Human Research Program: <https://www.nasa.gov/hrp/hazards>.
Code: `domain/spaceflight_context.py`. Radiation is **not** measured by any indicator (crews use dosimeters), and the app says so.

## Mission environments
Space station (low Earth orbit), deep-space transit vehicle, pressurized rover, Lunar base and Mars base. Each rates the five hazards Lower, Moderate or High with a one-line reason, and lists a health focus. Gravity, message delay and return time are shown.
The ratings are **qualitative orientation aids** written for this prototype, not mission requirements. The choice is saved per user in the browser and shown in:
- Mission overview (selector and facts),
- Spaceflight hazards (environment panel and a chip on every hazard card),
- the indicator detail window ("In your environment"),
- the text report.

## Measurement schedule
Each indicator has a suggested interval (24 hours, or 72 hours for blood glucose). The Daily assessment page shows ON SCHEDULE, DUE SOON, DUE NOW or NEVER RECORDED. Overdue indicators also appear in Attention and reminders. The mission protocol always sets the real schedule.

## Streaks and badges
Calculated in the browser from stored readings: current and best streak, days logged, points (10 per day logged and 25 per badge) and eight badges. Points reward logging only. They never depend on whether a value is good, so a poor reading cannot lose points.

Tests: `tests/unit/test_spaceflight_context.py`, `tests/integration/test_spaceflight_context_api.py`, `tests/integration/test_dashboard.py`.
