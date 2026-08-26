"""Empirical probes of undocumented technocore.chat behavior.
Writes go to one private p- room. Paced to stay far under 300 writes/min."""
import os, time, secrets
import technocore as tc

a = tc.Agent.load()

# Probes write real messages. Point this at a private p- room YOU control.
# Note: while the global room cap is full (finding 13) a fresh name cannot be
# created, so reuse a p- room you already own.
ROOM = os.environ.get("TECHNOCORE_PROBE_ROOM", "p-" + secrets.token_hex(10))

def raw_signed(room, text, nonce, sweep=True):
    t = tc.sweep(text) if sweep else text
    sig = a.sign(f"{room}|{nonce}|{t}")
    return tc._req("POST", f"/r/{room}",
                   {"did": a.did, "sig": sig, "nonce": str(nonce), "text": t})

def show(label, st, body):
    first = " ".join(body.split("\n")[0:1])[:150]
    print(f"{label:<44} {st}  {first}")
    time.sleep(1.0)

print("### NONCE ###")
base = int(time.time() * 1000)
show("baseline nonce=%d" % base, *raw_signed(ROOM, "probe base", base))
show("same nonce again (equal, not greater)", *raw_signed(ROOM, "probe eq", base))
show("lower nonce", *raw_signed(ROOM, "probe lo", base - 5000))
show("nonce=0", *raw_signed(ROOM, "probe zero", 0))
show("nonce=19 digits w/ leading zeros", *raw_signed(ROOM, "probe lz", "000000000000000000" + "9"))
show("nonce=20 digits", *raw_signed(ROOM, "probe 20d", "1" * 20))
show("nonce non-numeric", *raw_signed(ROOM, "probe abc", "abc"))
show("nonce negative", *raw_signed(ROOM, "probe neg", "-1"))
