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
| 1 | Foundation: data model, ingestion API, reference data, tests | **Done** (CI workflow pending) | |
| 2 | Offline queue, health status rules, personal baselines | Planned |
| 3 | Dashboard and interactive body map | Planned |
| 4 | Security: local authentication, audit log, encryption at rest | Planned |
| 5 | Resilience tests and full documentation | Planned |
| 6 | Release and submission package | Planned |

## What Phase 1 provides

- Data model for **missions**, **astronauts**, **measuring devices** and **health measurements**.
- Seven health indicators with units, "how to measure" instructions and "why it matters in spaceflight"
  explanations: heart rate, systolic and diastolic blood pressure, blood glucose, body temperature,
  sleep duration, mood score.
- Input validation that rejects impossible values (for example a heart rate of 7000) and future timestamps.
- REST API with automatic interactive documentation.
- Offline-capable storage (SQLite, no internet needed).

## Quick start

Requires Python 3.12 or newer.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[development]"
python -m astronaut_health_monitor
```

Open http://127.0.0.1:8000/docs for the interactive API documentation.

## API overview

| Method and path | Purpose |
|---|---|
| `GET /health` | Application and database status |
| `GET /health-indicators` | Explanation of every health indicator |
| `POST /missions`, `GET /missions` | Create and list missions |
| `POST /astronauts`, `GET /astronauts` | Register and list astronauts |
| `POST /measurements` | Record one measurement |
| `GET /measurements?astronaut_id=1` | List measurements, newest first (optional `indicator_type`, `limit`) |

Example:

```bash
curl -X POST http://127.0.0.1:8000/measurements -H "Content-Type: application/json" -d '{
  "astronaut_id": 1,
  "indicator_type": "heart_rate",
  "measured_value": 64,
  "measured_at": "2026-11-05T08:30:00+00:00"
}'
```

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
tests/            unit and integration tests
docs/             architecture documentation
```

See [docs/architecture.md](docs/architecture.md) and [CONTRIBUTING.md](CONTRIBUTING.md).

## Acknowledgements

Indicator selection follows the challenge brief and the five spaceflight hazards identified by NASA's
Human Research Program: radiation, isolation and confinement, distance from Earth, gravity fields,
and hostile closed environments.
