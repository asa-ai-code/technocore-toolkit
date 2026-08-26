import { keyFromSeed, sweep, signMessage } from "./technocore.mjs";
const key = keyFromSeed(Buffer.from(Array.from({length:32},(_,i)=>i)));
let pass = 0, fail = 0;
const check = (label, got, want) => {
  const ok = got === want;
  ok ? pass++ : fail++;
  console.log(`${ok ? "PASS" : "FAIL"}  ${label}`);
  if (!ok) console.log(`      got  ${got}\n      want ${want}`);
};
check("did:key", key.did, "did:key:z6MkehRgf7yJbgaGfYsdoAsKdBPE3dj2CYhowQdcjqSJgvVd");
const V = [
 ["lobby",1,"hello","hello","3dwq_rDu9g6evu6yGvOdMGqmh5R5jz5geYWwHddflXuSX602xR7gCznZ1KBpXqBGxZF4_tzQU7Sr_EVPRJ5JAg"],
 ["lobby",1755000000000,"check-in","check-in","hjmYs3A5w9MR7EE5Y12VnvkSNzVcIHaHvbU34dYAcHoH8JIU9NcpXRIDCgbZ72F1Wm1aC7wGHCReMGx0OSJnBw"],
 ["meta",42,"a‍b","a b","Y_E5aZj0i780R1Luzm_3XO8TQ0R9MlocKYYiVc6dS6PX0OyTqYxJ3eGi9V_BRrpAw6YKdQelE-yQJbGpwBWUBg"],
 ["meta",43,"tab\there","tab here","XwqoyXcGu18_kpfK-rky7uQpcTVbIEsNamR-5wpD_-J72kVbSix59z9uCPWN6pA_WWYjuZV0ViwRJBogauPSBg"],
 ["meta",44,"  a‍b \t c  ","a b   c","_TGsBBnfGcXR9KTLOmhfHY1kY-IONQ94-Kqn68GaFtnu84zAZLMj_MIkmHjJp_LDU2imYwUQs5rnB7pkw1ZrAQ"],
 ["meta",45,"　y　","y","-mTj8lIJM8upu3eqScvi0JZiWsEzEHJC2kfCsvnmfjk2a1o6Rk5m4uAxviRGgPsmk-xNHLKdNevB3clpqlSQAg"],
];
for (const [room,nonce,raw,wantText,wantSig] of V) {
  check(`sweep  [${nonce}]`, sweep(raw), wantText);
  check(`sig    [${nonce}]`, signMessage(key, room, nonce, raw).sig, wantSig);
}
console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
