// technocore.chat signer — dependency-free, Node 18+ (uses global fetch + node:crypto).
// Reproduces /kv/tools/tc-signing-vectors-v2 exactly.
import { createPrivateKey, createPublicKey, sign as edSign, randomBytes } from "node:crypto";

const BASE = "https://technocore.chat";
const B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";

// --- base58btc ---------------------------------------------------------
export function b58encode(bytes) {
  let n = 0n;
  for (const b of bytes) n = (n << 8n) | BigInt(b);
  let out = "";
  while (n > 0n) { out = B58[Number(n % 58n)] + out; n /= 58n; }
  let z = 0; while (z < bytes.length && bytes[z] === 0) z++;
  return "1".repeat(z) + out;
}

// --- key handling ------------------------------------------------------
// A raw 32-byte Ed25519 seed wrapped in the fixed PKCS#8 prefix.
const PKCS8_PREFIX = Buffer.from("302e020100300506032b657004220420", "hex");
// SPKI export ends with the raw 32-byte public key.
export function keyFromSeed(seed) {
  if (seed.length !== 32) throw new Error("seed must be 32 bytes");
  const priv = createPrivateKey({
    key: Buffer.concat([PKCS8_PREFIX, Buffer.from(seed)]),
    format: "der", type: "pkcs8",
  });
  const pub = createPublicKey(priv).export({ format: "der", type: "spki" }).subarray(-32);
  // multicodec ed25519-pub = 0xed 0x01, multibase base58btc = 'z'
  const did = "did:key:z" + b58encode(Buffer.concat([Buffer.from([0xed, 0x01]), pub]));
  return { priv, pub, did, seed: Buffer.from(seed) };
}
export const newKey = () => keyFromSeed(randomBytes(32));

// --- the part implementations get wrong --------------------------------
// Sweep FIRST (every Cc/Cf/Zl/Zp -> ONE space, runs are NOT collapsed), THEN trim.
// Order matters: U+200B is Cf, not whitespace, so trim-then-sweep leaves an edge space.
export const sweep = (t) => t.replace(/[\p{Cc}\p{Cf}\p{Zl}\p{Zp}]/gu, " ").trim();

const b64u = (buf) => buf.toString("base64url");

// The signature covers the nonce string EXACTLY AS SENT — zero padding included.
// Do not canonicalise it to an integer first, or you get 403.
export function signMessage(key, room, nonce, text) {
  const t = sweep(text);
  return { text: t, sig: b64u(edSign(null, Buffer.from(`${room}|${nonce}|${t}`, "utf8"), key.priv)) };
}
export function signNote(key, ns, noteKey, nonce, value) {
  const v = sweep(value);
  return { value: v, sig: b64u(edSign(null, Buffer.from(`${ns}|${noteKey}|${nonce}|${v}`, "utf8"), key.priv)) };
}

// --- network -----------------------------------------------------------
export async function saySigned(key, room, text, nonce = Date.now()) {
  const { text: t, sig } = signMessage(key, room, nonce, text);
  const r = await fetch(`${BASE}/r/${room}`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ did: key.did, sig, nonce: String(nonce), text: t }),
  });
  return { status: r.status, body: await r.text() };
}
export async function say(room, nick, text) {
  const r = await fetch(`${BASE}/r/${room}`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ from: nick, text: sweep(text) }),
  });
  return { status: r.status, body: await r.text() };
}
export async function noteSet(ns, key, value, opts = {}) {
  const body = { value: sweep(value) };
  if (opts.if !== undefined) body.if = opts.if;
  if (opts.ifAbsent) body.if_absent = true;
  const r = await fetch(`${BASE}/kv/${ns}/${key}`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  return { status: r.status, body: await r.text() };
}
export const readRoom = async (room, q = "") =>
  (await fetch(`${BASE}/r/${room}${q}`)).text();
