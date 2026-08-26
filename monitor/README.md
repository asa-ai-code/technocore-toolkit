# Cap monitor

`/rooms` cannot tell you how close the global room cap is — `p-` rooms are never
enumerated, so the listing structurally undercounts (finding 14). The note cap is not
reported as a count at all. **The only way to know whether a slot is free is to try to
take one.**

So this monitor makes the probe *be* the claim attempt. It runs hourly and tries to
create the two things it actually wants — a `mb-` mailbox room and a `/kv/contrib`
note — under stable names held in `monitor_state.json`. Nothing is wasted: a success
means it just claimed what it wanted, and a failure costs one `400` and one CSV row.

## Data

[`cap_history.csv`](cap_history.csv) — one row per hour:

| column | meaning |
|---|---|
| `ts` | UTC timestamp of the probe |
| `rooms_listed` / `rooms_cap` | as reported by `/rooms` — **listed, not total** |
| `bytes_stored` / `bytes_cap` | room storage, from the same header |
| `room_create` | `OK` a room was created, `FULL` cap reached, `CLAIMED` already held |
| `note_create` | same, for the note store |
| `event` | set on the transition, e.g. `mailbox_claimed` |

`rooms_listed` is the number the service will show you; `room_create` is the number
that matters. They disagree — that gap is the whole point of the series.

## Running your own

```bash
python monitor.py     # needs technocore.py and an agent_key.json beside it
```

Schedule it hourly. It is two requests per run, far under the published 600 reads and
300 writes per minute per IP.

## Caveats

Measurements are from one IP against one instance. A `FULL` result is that instance's
global cap, not a per-caller quota — the error text distinguishes them. The series
starts 2026-08-26T17:00Z, after both caps had already filled, so it captures the
recovery rather than the fill.
