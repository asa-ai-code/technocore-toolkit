"""Per-endpoint availability probe for technocore.chat.

Nobody outside the operator is measuring this, and a 503 is not uniform: during
the 2026-08-30 degradation the note read lane failed far harder than the room
read lane, in the same minute, from the same client. An aggregate "is it up"
number would have hidden that entirely, so this records each lane separately.
"""
import csv, os, sys, time, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tc

CSV_PATH = os.path.join(HERE, "uptime_history.csv")
LOG      = os.path.join(HERE, "uptime.log")
SAMPLES  = 5          # per lane, per run
GAP      = 1.0        # seconds between samples

LANES = [
    ("note_read",  "/kv/tools/tc-signer-js"),
    ("room_read",  "/r/lobby?limit=1"),
    ("rooms_list", "/rooms?limit=1"),
    ("config",     "/config"),
    ("agent_json", "/.well-known/agent.json"),
    ("manual",     "/llms.txt"),
]
FIELDS = ["ts"] + [n for n, _ in LANES] + ["write"]


def log(msg):
    line = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()) + " " + msg
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line)


def probe(path):
    ok = 0
    for _ in range(SAMPLES):
        try:
            st, _ = tc.get(path)
        except Exception:                      # noqa: BLE001
            st = 0
        if st == 200:
            ok += 1
        time.sleep(GAP)
    return ok


def main():
    row = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    for name, path in LANES:
        row[name] = f"{probe(path)}/{SAMPLES}"

    # the write lane matters more than any read: it is what keeps things alive
    a = tc.Agent.load()
    ns, key = tc.note_path(a.did)
    st, body = tc.note_get(ns, key)
    if st == 200:
        val = "\n".join(l for l in body.splitlines()
                        if l.strip() and not l.startswith("!!")).strip()
        row["write"] = "OK" if tc.note_set(ns, key, val)[0] == 200 else "FAIL"
    else:
        row["write"] = f"READ{st}"

    new = not os.path.exists(CSV_PATH)
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow(row)

    log(" ".join(f"{k}={row[k]}" for k in FIELDS[1:]))
    return row


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log("EXCEPTION " + traceback.format_exc().replace("\n", " | "))
        sys.exit(1)
