# Contributing

1. Create a branch per change (`phase-2-offline-queue`, `fix-glucose-bounds`, ...).
2. Keep layers separate: API calls services, services call repositories, `domain` has no outside dependencies.
3. Use descriptive names (`measured_value`, not `val`).
4. Before committing run: `ruff check . && ruff format . && mypy src tests && pytest`.
5. New business rules need tests; critical modules must stay at or above 80% coverage.
6. Commit messages: short imperative summary, for example `Add measurement validation`.
