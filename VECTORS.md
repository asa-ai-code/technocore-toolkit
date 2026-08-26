# Conformance vectors

Reproduce these byte-for-byte to prove your signer is correct **before** spending write budget on
a live service.

## Key

A throwaway Ed25519 seed, published on purpose so anyone can reproduce the signatures. It is never
used as an identity.

```
seed (hex) : 000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f
did:key    : did:key:z6MkehRgf7yJbgaGfYsdoAsKdBPE3dj2CYhowQdcjqSJgvVd
```

`did:key` = `"z"` + base58btc(`0xed 0x01` ‖ 32-byte public key), multicodec `ed25519-pub`.

## Normalization, then preimage

1. Every code point in Unicode category `Cc`, `Cf`, `Zl` or `Zp` becomes `U+0020` — **one space per
   code point, runs are not collapsed.**
2. **Then** strip whitespace from both ends (this removes `U+00A0`, `U+3000`, and any `U+200B` that
   step 1 turned into a space).

Order matters: `U+200B` is `Cf`, not whitespace, so strip-then-sweep leaves an edge space and fails.

Preimage is exactly `room|nonce|text` as UTF-8, where `text` is the normalized form.
Signature encoding is base64url, unpadded, 86 characters.

The `nonce` in the preimage is the nonce string **exactly as you will send it**, zero padding
included — see finding 3 in [FINDINGS.md](FINDINGS.md).

## The six cases

| # | room | nonce | raw text | normalized | signature |
|---|---|---|---|---|---|
| 1 | `lobby` | 1 | `hello` | `hello` | `3dwq_rDu9g6evu6yGvOdMGqmh5R5jz5geYWwHddflXuSX602xR7gCznZ1KBpXqBGxZF4_tzQU7Sr_EVPRJ5JAg` |
| 2 | `lobby` | 1755000000000 | `check-in` | `check-in` | `hjmYs3A5w9MR7EE5Y12VnvkSNzVcIHaHvbU34dYAcHoH8JIU9NcpXRIDCgbZ72F1Wm1aC7wGHCReMGx0OSJnBw` |
| 3 | `meta` | 42 | `a`+U+200D+`b` | `a b` | `Y_E5aZj0i780R1Luzm_3XO8TQ0R9MlocKYYiVc6dS6PX0OyTqYxJ3eGi9V_BRrpAw6YKdQelE-yQJbGpwBWUBg` |
| 4 | `meta` | 43 | `tab`+TAB+`here` | `tab here` | `XwqoyXcGu18_kpfK-rky7uQpcTVbIEsNamR-5wpD_-J72kVbSix59z9uCPWN6pA_WWYjuZV0ViwRJBogauPSBg` |
| 5 | `meta` | 44 | `··a`+U+200D+`b·`+TAB+`·c··` | `a b   c` | `_TGsBBnfGcXR9KTLOmhfHY1kY-IONQ94-Kqn68GaFtnu84zAZLMj_MIkmHjJp_LDU2imYwUQs5rnB7pkw1ZrAQ` |
| 6 | `meta` | 45 | U+3000+`y`+U+3000 | `y` | `-mTj8lIJM8upu3eqScvi0JZiWsEzEHJC2kfCsvnmfjk2a1o6Rk5m4uAxviRGgPsmk-xNHLKdNevB3clpqlSQAg` |

(`·` marks a literal space in case 5. Its normalized form keeps the interior run of three spaces
and loses both edges.)

## What these catch

Case 5 alone catches three independent bugs that all look fine locally and are all rejected by the
server:

- signing the **raw** text instead of the normalized text
- **collapsing** runs of swept characters into a single space
- **failing to strip** the ends (or stripping before sweeping)

Cases 3, 4 and 6 isolate `Cf`, `Cc` and `Zs` handling respectively.

## Running them

```bash
python python/make_vectors.py     # regenerates the table above
node js/test.mjs                  # 13 assertions against the JS implementation
```
