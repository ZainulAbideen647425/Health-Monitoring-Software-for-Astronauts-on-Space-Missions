# Resilience and failure behaviour

The monitor is meant for places where help is far away, so every failure must be **safe, visible and recoverable**.
These behaviours are checked by `tests/integration/test_resilience.py`.

| Failure | What the system does | Test |
|---|---|---|
| Wrong, missing or out-of-range input (bad indicator, text instead of number, absurd value, no timezone, over-long note) | Refused with a 4xx message. Nothing is stored. | `test_invalid_readings_are_refused...` |
| Broken JSON or wrong body shape | 422, never a crash | `test_non_json_and_wrong_shaped_bodies...` |
| Unknown astronaut or reading | 404 / 403, never a 500 | `test_unknown_records...` |
| Same reading sent many times (retry after a lost reply) | One stored record, thanks to `client_reference` | `test_repeated_submissions...` |
| Batch with some bad items | Good items are kept, bad ones are reported one by one | `test_a_batch_with_good_and_bad_items...` |
| Repeated wrong passwords | Account is locked for a period | `test_account_locks...` |
| No session | 401 on every health route | `test_requests_without_a_session...` |
| Connection lost during offline synchronisation | Items stay in the local queue and are sent later | `test_offline_queue_survives...` |
| Server answers only part of a batch | Unanswered items stay queued | `test_a_half_answered_batch...` |
| Damaged queue file | Clear error, the file is left untouched for recovery | `test_a_damaged_queue_file...` |
| Database encrypted with a different key | Clear message telling the user how to reset (see README) | `test_authentication_api.py` |
| Browser offline | Banner and OFFLINE indicator; last data stays on screen | dashboard script |

## Known limits (honest list)
- The offline queue is a local file, not a full offline app. Readings entered in the browser while offline are not queued.
- Status rules are educational reference ranges, not a clinical device.
- SQLite is single-writer. A real mission would need a replicated store.
- No automated browser test runs in CI. The dashboard was checked by hand with Playwright.
