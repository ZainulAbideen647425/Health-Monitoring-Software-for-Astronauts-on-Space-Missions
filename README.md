# Astronaut Health Monitor

Health monitoring software for astronauts on long space missions, built for the
**2026 NASA Space Apps Challenge: "Create Health Monitoring Software for Astronauts on Space Missions"**.

On long missions, astronauts carry much of the responsibility for spotting health changes in themselves.
This software collects health indicators, helps the astronaut understand them, and (in later phases) shows
their status at a glance and suggests actions.

> **Disclaimer:** This is an educational prototype for a hackathon. It is not a medical device and must not be
> used for real medical decisions.

## Project status

| Phase | Content | Status |
|---|---|---|
| 1 | Foundation: data model, ingestion API, reference data, tests, CI | **Done** |
| 2 | Health status rules, personal baselines, guidance, offline queue | **Done** |
| 3 | Dashboard and interactive body map | **Done** (core version) |
| 4 | Security: local authentication, audit log, encryption at rest | Planned |
| 5 | Resilience tests and full documentation | Planned |
| 6 | Release and submission package | Planned |

## The dashboard (Phase 3)

One self-contained page, served by the app itself with no internet or external libraries:

- **Body map:** click head, chest, abdomen or legs to see the organ's function, the spaceflight hazard that affects it,
  and the status of its indicators. Each region's outline is colored by its worst status.
- **Status cards:** one per indicator with status label (text and symbol, not color alone), reasons, and actions.
  Critical readings show a clear "contact the flight surgeon" alert.
- **History chart:** readings over time with the expected range shaded.
- **Measurement form:** shows how to measure the chosen indicator and judges the reading immediately.
- **Demo crew:** one click creates a sample astronaut with 14 days of readings.

Not yet included: multiple mission environments, gamification, report export, and a bone indicator for the legs.

## What phases 1 and 2 provide

- Data model for **missions**, **astronauts**, **measuring devices** and **health measurements**.
- Seven health indicators with units, "how to measure" instructions and "why it matters in spaceflight"
  explanations: heart rate, systolic and diastolic blood pressure, blood glucose, body temperature,
  sleep duration, mood score.
- Input validation that rejects impossible values (for example a heart rate of 7000) and future timestamps.
- REST API with automatic interactive documentation.
- Offline-capable storage (SQLite, no internet needed).
- **Health status rules** (normal, caution, critical) for every indicator, with documented sources.
- **Personal baselines and trend detection**: a reading is also judged against the astronaut's own recent history,
  so a slow drift is flagged even while values are still in the normal range.
- **Guidance** for every out-of-range reading: explanation, likely causes, recommended actions, warning signs,
  and a clear "contact the flight surgeon" trigger for critical readings.
- **Offline queue and safe synchronization**: measurements taken without a connection are stored durably and sent
  later; unique client references guarantee that retries never create duplicates.

## Quick start

Requires Python 3.12 or newer.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[development]"
python -m astronaut_health_monitor
```

Open http://127.0.0.1:8000/ for the dashboard (click **Load demo crew** to see sample data) and
http://127.0.0.1:8000/docs for the interactive API documentation.

## API overview

| Method and path | Purpose |
|---|---|
| `GET /health` | Application and database status |
| `GET /health-indicators` | Explanation of every health indicator |
| `POST /missions`, `GET /missions` | Create and list missions |
| `POST /astronauts`, `GET /astronauts` | Register and list astronauts |
| `POST /measurements` | Record one measurement |
| `GET /measurements?astronaut_id=1` | List measurements, newest first (optional `indicator_type`, `limit`) |
| `POST /measurements/batch` | Store up to 500 queued measurements; every item gets its own result |
| `GET /measurements/{id}/assessment` | Judge one measurement: status, personal baseline, trend, guidance |
| `GET /astronauts/{id}/health-summary` | Latest assessment of every indicator and an overall status |
| `GET /health-status-rules` | The ranges, critical limits and sources used for judging |

Example:

```bash
curl -X POST http://127.0.0.1:8000/measurements -H "Content-Type: application/json" -d '{
  "astronaut_id": 1,
  "indicator_type": "heart_rate",
  "measured_value": 64,
  "measured_at": "2026-11-05T08:30:00+00:00"
}'
```

### Upgrading from Phase 1

Phase 2 adds a column (`client_reference`) to the measurements table. There is no migration tool yet, so delete
the old `astronaut_health_monitor.db` file once; it is recreated automatically on the next start.

## Development

```bash
pytest                 # tests, fails below 80% coverage
ruff check .           # lint
ruff format --check .  # formatting
mypy src tests         # type check
```

## Project structure

```
src/astronaut_health_monitor/
  api/            HTTP endpoints, request/response shapes
  services/       business rules (validation, recording, reading)
  repositories/   database access and table definitions
  domain/         indicator vocabulary, reference data, errors
  core/           configuration and database setup
  offline_synchronization/   local queue that stores measurements until a connection exists
tests/            unit and integration tests
docs/             architecture documentation
```

See [docs/architecture.md](docs/architecture.md), [docs/health_status_rules.md](docs/health_status_rules.md), [docs/offline_synchronization.md](docs/offline_synchronization.md) and [CONTRIBUTING.md](CONTRIBUTING.md).

## Acknowledgements

Indicator selection follows the challenge brief and the five spaceflight hazards identified by NASA's
Human Research Program: radiation, isolation and confinement, distance from Earth, gravity fields,
and hostile closed environments.
