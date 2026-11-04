# Offline queue and synchronization (Phase 2)

## Problem

A spacecraft or a base on the Moon or Mars may have no connection to the main system for hours or days.
Measurements must never be lost, and must never be stored twice when the connection returns.

## Design

```
device                                                    main system
------                                                    -----------
enqueue_measurement()  -> local queue file (JSON)
        ...time passes, maybe offline...
synchronize(send_batch) -> POST /measurements/batch  ---> each item: created / duplicate / rejected
        <-- per-item results ----------------------------
created or duplicate  -> removed from queue
rejected              -> moved to "rejected" list with the reason (not retried)
connection error      -> everything stays queued
```

## Guarantees

- **Durable:** every enqueue is written to disk immediately. The file is saved by writing a temporary file and then
  replacing the old one, so a crash cannot leave a half-written queue.
- **No duplicates (idempotency):** each measurement gets a unique `client_reference`. The server stores it in a unique
  column. Sending the same reference again returns `duplicate` and creates nothing, even if the first reply was lost.
  If two requests race, the database unique constraint decides and the loser receives the winner's record.
- **No blocking:** one bad item (unknown astronaut, impossible value, malformed fields) is rejected on its own and
  never blocks the others. Malformed items are validated one by one on the server for this reason.
- **Bounded batches:** at most 500 items per request; the client sends 100 per request by default.

## What is not built yet

- The HTTP sender that connects `synchronize` to a real URL (the function is passed in, so it is easy to add and to test).
- Synchronization of missions, astronauts and devices; only measurements are queued.
- Encryption of the queue file (Phase 4).
