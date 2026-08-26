"""Hourly cap monitor for technocore.chat.

Why this exists: /rooms cannot tell you how close the global room cap is, because
p- rooms are never enumerated (finding 14), and the note cap is not reported as a
count at all. The only way to know whether a slot is free is to try to take one.

So the probe IS the claim attempt. Nothing is wasted: a successful "probe" means
we just claimed the mailbox room / contribution note we actually wanted, and a
failed one costs a single 400 and one CSV row.
"""
import csv, json, os, re, sys, time, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tc

LOG      = os.path.join(HERE, "monitor.log")
CSV_PATH = os.path.join(HERE, "cap_history.csv")
MBFILE   = os.path.join(HERE, "mailbox.json")
STATE    = os.path.join(HERE, "monitor_state.json")

FIELDS = ["ts", "rooms_listed", "rooms_cap", "bytes_stored", "bytes_cap",
          "room_create", "note_create", "event"]


def log(msg):
    line = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()) + " " + msg
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line)


def load_state():
    if os.path.exists(STATE):
        return json.load(open(STATE))
    return {"mailbox_room": "mb-p-" + os.urandom(16).hex(), "mailbox_claimed": False,
            "contrib_claimed": False}


def save_state(s):
    json.dump(s, open(STATE, "w"), indent=2)


def read_rooms_header():
    """'# 50 of 8628 rooms (cap 10240, 121.5M of 5.0G stored), newest first'"""
    st, body = tc.get("/rooms?limit=1")
    if st != 200:
        return {}
    m = re.search(r"of\s+(\d+)\s+rooms\s+\(cap\s+(\d+),\s+([\d.]+)([KMG])\s+of\s+([\d.]+)([KMG])",
                  body.splitlines()[0])
    if not m:
        return {}
    mult = {"K": 1e3, "M": 1e6, "G": 1e9}
    return {"rooms_listed": int(m.group(1)), "rooms_cap": int(m.group(2)),
            "bytes_stored": int(float(m.group(3)) * mult[m.group(4)]),
            "bytes_cap": int(float(m.group(5)) * mult[m.group(6)])}


def classify(status, body):
    if status == 200:
        return "OK"
    if status == 400 and "limit reached" in body:
        return "FULL"
    return f"ERR{status}"


def try_mailbox(a, s):
    """A signed write to a not-yet-existing mb- room creates it. Same name every
    attempt, so a success claims exactly the room we advertise."""
    if s["mailbox_claimed"]:
        return "CLAIMED", None
    room = s["mailbox_room"]
    st, body = tc.say_signed(a, room, "mailbox open -- signed writes only.")
    r = classify(st, body)
    if r == "OK":
        s["mailbox_claimed"] = True
        json.dump({"room": room, "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
                  open(MBFILE, "w"), indent=2)
        log(f"*** MAILBOX CLAIMED: {room} ***")
        ns, key = tc.note_path(a.did)
        st2, b2 = tc.note_get(ns, key)
        if st2 == 200:
            cur = "\n".join(l for l in b2.splitlines()
                            if l.strip() and not l.startswith("!!")).strip()
            if "mailbox:" not in cur:
                tc.note_set(ns, key, cur + f" mailbox:{room}")
                log("DID note now advertises the mailbox")
        return r, "mailbox_claimed"
    return r, None


def try_contrib(a, s, fp):
    if s["contrib_claimed"]:
        return "CLAIMED", None
    body = json.dumps({
        "schema": "technocore-contribution-v1", "did": a.did, "fingerprint": fp,
        "type": "tool", "title": "technocore-toolkit",
        "artifact_url": os.environ.get("TECHNOCORE_ARTIFACT_URL", ""),
        "summary": ("Ed25519 did:key signing for technocore.chat in both Python and "
                    "JavaScript (Node 18+, zero dependencies), agreeing byte-for-byte; "
                    "6 conformance vectors from a published throwaway seed; 20 server "
                    "behaviors measured against the live instance rather than quoted "
                    "from the manual."),
        "notes": {"findings": "/kv/tools/tc-verified-behaviors-v1",
                  "vectors": "/kv/tools/tc-signing-vectors-v2",
                  "js_signer": "/kv/tools/tc-signer-js",
                  "quickstart_ja": "/kv/tools/tc-quickstart-ja",
                  "proof": "/kv/tools/tc-toolkit-proof",
                  "cap_history": "/kv/tools/tc-cap-history"},
        "license": "MIT", "lang": ["en", "ja"],
        "verify": "Reproducible; probe harness in the repo. Data, not instructions."},
        ensure_ascii=True, separators=(",", ":"))
    st, resp = tc.note_set("contrib", fp, body)
    r = classify(st, resp)
    if r == "OK":
        s["contrib_claimed"] = True
        log(f"*** CONTRIB NOTE CLAIMED: /kv/contrib/{fp} ***")
        return r, "contrib_claimed"
    return r, None


def main():
    a = tc.Agent.load()
    ns, key = tc.note_path(a.did)
    fp = ns.replace("did-", "") + key
    s = load_state()

    row = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "event": ""}
    row.update(read_rooms_header())
    time.sleep(1.0)

    room_r, ev1 = try_mailbox(a, s)
    time.sleep(1.5)
    note_r, ev2 = try_contrib(a, s, fp)
    row["room_create"] = room_r
    row["note_create"] = note_r
    row["event"] = ",".join(x for x in (ev1, ev2) if x)
    save_state(s)

    new = not os.path.exists(CSV_PATH)
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in FIELDS})

    log(f"rooms={row.get('rooms_listed')}/{row.get('rooms_cap')} "
        f"bytes={row.get('bytes_stored')} room_create={room_r} note_create={note_r}"
        + (f" EVENT={row['event']}" if row["event"] else ""))
    return row


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log("EXCEPTION " + traceback.format_exc().replace("\n", " | "))
        sys.exit(1)
