# Architecture (phases 1 and 2)

```
HTTP client
   |
   v
api/ (FastAPI routes, request/response schemas, error mapping)
   |
   v
services/ (business rules: existence checks, plausibility, timestamp checks)
   |
   v
repositories/ (queries) --> SQLite database (offline, single file)

domain/ (indicator types, reference data, status rules, guidance, baseline math, exceptions)
        is used by all layers and depends on nothing.

offline_synchronization/ (local queue file) sits beside the API: it sends batches to POST /measurements/batch.
```

## Key decisions

- **SQLite:** works without a network, which matches missions with delayed or no connection to Earth.
- **Layered design:** later phases (status rules, offline queue, dashboard) plug into services without touching the API or database code.
- **Plausibility limits, not clinical limits:** Phase 1 only rejects values no living person could show.
  Clinical status rules (normal, caution, critical) arrive in Phase 2 and will be sourced from NASA and other space-agency references.
- **Timestamps are always timezone-aware and stored in UTC.**
- **Clock tolerance:** a measurement up to 5 minutes in the future is accepted, because spacecraft device clocks drift.

## Data model

- `missions`: name, environment (spacecraft, space station, lunar base, Mars base, rover), start time
- `astronauts`: name, mission role, optional mission
- `devices`: name, device kind
- `measurements`: astronaut, indicator, value, unit, time, source, optional device, notes

## Phase 2 additions

- **Rules are data, not code paths:** each indicator has a `HealthStatusRule` (ranges, critical limits, sources) and
  one shared evaluation method. Adding an indicator means adding one rule and its guidance, not new logic.
- **Assessment = rule + personal baseline + trend:** see docs/health_status_rules.md.
- **Idempotent writes:** a `client_reference` column (unique) makes retries safe. See docs/offline_synchronization.md.
- **Assessments are computed on demand, not stored,** so changing a rule immediately changes every judgement
  and there is no stale data to migrate.

## Phase 4 additions

- **Sign-in, roles and audit** live in services (`authentication_service`, `audit_service`) and pure rules (`domain/permissions.py`);
  the API layer only asks 'may this user do this?' through dependencies and `api/authorization.py`.
- **Encrypted columns** are database types (`core/encrypted_types.py`), so repositories and services are unchanged.
- Full design and limits: docs/security.md.

## Known limits

- No endpoints to create devices yet (the table and repository exist).
- The dashboard is a single page with no build step; it is not yet covered by browser-level automated tests
  (the tests check that it is served, has its features, uses no external resources and calls only existing endpoints).
- No database migration tool: changing a table currently means recreating the local database file.
