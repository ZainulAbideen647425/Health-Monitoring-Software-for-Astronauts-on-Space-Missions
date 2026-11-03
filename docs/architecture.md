# Architecture (Phase 1)

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

domain/ (indicator types, reference data, exceptions) is used by all layers and depends on nothing.
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

## Known limits in Phase 1

- No authentication or encryption at rest (Phase 4).
- No endpoints to create devices yet (the table and repository exist).
- No health status evaluation yet (Phase 2).
