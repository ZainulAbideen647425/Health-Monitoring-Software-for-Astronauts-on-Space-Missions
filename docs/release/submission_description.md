# NASA Space Apps Challenge 2026 submission

**Project name:** Astronaut Health Monitor
**Challenge:** Health monitoring software for astronauts on space missions
**Team:** Solo, Zain (University of South Asia, BS Software Engineering)
**Repository:** https://github.com/ZainulAbideen647425/Health-Monitoring-Software-for-Astronauts-on-Space-Missions

## Summary (about 100 words)
Astronaut Health Monitor is an offline-first web app that helps crew members watch their own health on long missions, when ground control is minutes away. It records heart rate, blood pressure, glucose, temperature, sleep, mood, fatigue, stress and activity, compares each reading with a safe range and a personal baseline, and explains the result with plain-language steps and a flight-surgeon escalation signal. A dashboard shows readiness, body-system context, trends and spaceflight hazards. Data is encrypted, access is role-based, and every action is written to a tamper-evident audit log.

## What it does
Readiness overview, body map and systems, trends and pattern detection, daily check-in, rule-based health intelligence, printable reports, offline queue with safe sync, self-registration with strong passwords.

## How it was built
Python, FastAPI, SQLAlchemy, SQLite, Pydantic; single-file dashboard with no external resources; pytest, ruff, mypy, GitHub Actions.

## Use of NASA data and references
Reference ranges draw on public guidance from the American Heart Association, American Diabetes Association, CDC and WHO, and on a published study of astronaut sleep (Barger et al.). The five hazard cards summarise widely documented spaceflight effects. Sources and their limits are listed in `docs/health_status_rules.md`. No NASA dataset is used. Sample data is simulated and labelled as such.

## Limits
Not a clinical device. Ranges are generic. See `docs/resilience.md`.

## Future work
Learned anomaly models trained on public analogue data, wearable ingestion, multilingual guidance, mobile client.
