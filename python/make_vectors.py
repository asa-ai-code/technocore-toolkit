"""Deterministic conformance vectors for the technocore signing scheme.
Throwaway seed, published on purpose, never an identity."""
import json
import technocore as tc

a = tc.Agent(bytes(range(32)))
CASES = [
    ("lobby", 1, "hello"),
    ("lobby", 1755000000000, "check-in"),
    ("meta", 42, "a\u200db"),                 # ZWJ (Cf) -> space, 1:1
    ("meta", 43, "tab\there"),                # C0 control -> space
    ("meta", 44, "  a\u200db \t c  "),        # sweep then strip; interior run kept
    ("meta", 45, "\u3000y\u3000"),            # U+3000 edges stripped
]
print("did:", a.did)
for room, n, raw in CASES:
    t = tc.sweep(raw)
    print(json.dumps({"room": room, "nonce": n, "raw": raw, "swept": t,
                      "sig": a.sign(f"{room}|{n}|{t}")}, ensure_ascii=True))
