# WAVE-21 — AeroSkills build (concurrency-capped fan-out)

Source: relay CEO 2026-09-01 ~20:55 UTC. WAVE-20 GATE PASSED 9.55/10 —
CEO FRESH replay at HEAD 38c0b33 (validate 5/5 602/602 · attest 3/3 ·
run-tests ALL PASS incl G7 + N53/N54 + N49/N50 + G1-G8 · em dashes 0 ·
tree clean · remote == 38c0b33 private push verified · GROUP 160 post
SEND_EXIT=0). G7 resolution: design session RETIRED docs/domain-map.svg in
Design v6 (447b45d) — the stale-count file no longer exists on main, G7
green at HEAD; no counts edit applied (correct).

Baseline for WAVE-21: HEAD 38c0b33 == remote main (private
arjun-0077/aeroskills, publish law — NO Ashforde). Live tree:
**294 leaves + 12 routers = 306 SKILL.md** (per-family: aerodynamics 26 ·
avionics 26 · cross-cutting 26 · flight-test-operations 26 ·
manufacturing-quality 26 · structures 26 · flight-mechanics 25 ·
gnc-autonomy 25 · propulsion 25 · space-systems 25 ·
systems-engineering-safety 25 · vehicle-design 25). Corpus **602** tasks.
Ratings ledger 296 rows (294 leaves, all ≥9.5). Em dashes 0 skills/.

## STEP 0 — TURN-ALIVE (HARD — 3 prior occurrences, wave-16/19/20)
Previous runs died because the bot wrote a **text response** while async
delegations were LIVE. A text response ENDS the turn and the CLI tears down
live delegations ("Interrupted N async delegation(s) (CLI shutdown)").

HARD RULES:
1. **NEVER write your final text response while any delegation is live.**
   The ONLY text response is the close-out, AFTER every subagent has
   completed AND you have verified their commits.
2. Mid-build status = GROUP 160 post via the `hermes send` TOOL (a tool
   call) — never via a text response.
3. Stay alive by POLLING with tool calls (delegation status, task logs,
   git log, ps) until ALL subagents complete. Do not end the turn early.
4. If the CLI is externally killed mid-wave: resume from committed leaves
   only — incremental commits are the only durable record.

## STEP 1 — API HEALTH FIRST
Check DeepSeek API health (429/402). If degraded → build SEQUENTIALLY, one
leaf at a time, commit each immediately, NO fan-out; re-test every 3
leaves. Fan-out ONLY if healthy, CAP 3-4 concurrent subagents (API limit 5).
If balance exhausted → STOP CLEAN: state note "BALANCE BLOCKED — founder
must top up DeepSeek", NO fake gates, no founder contact beyond the note.

## STEP 2 — FAN-OUT (ONE SUBAGENT PER SKILL)
Target +10-16 verified leaves, MUST land ≥10. Family order:
six 25-count families FIRST: flight-mechanics → gnc-autonomy → propulsion →
space-systems → systems-engineering-safety → vehicle-design.
Then 26-count if headroom: aerodynamics → avionics → cross-cutting →
flight-test-operations → structures → manufacturing-quality.

ONE subagent per skill; each subagent builds (brainstorm → SKILL.md +
scripts/ contract test + corpus tasks + standards-map ext), runs make
validate for its leaf, commits own leaf immediately (7-rule, explicit paths
only — NO `git add -A` / `git reset`; index-lock retry).

## STEP 3 — RATE-AT-CREATION (mandate)
Every new leaf rated ≥9.5 in eval/skill-ratings.md IN THE SAME BUILD TURN
(rebuild in-turn if below; leaf not done until rated). Ledger advances
294 → 294+N.

## STEP 4 — CLOSE-OUT CHAIN (all gates FRESH, no exceptions)
1. Corpus 602 → 602+2N (merge eval fragments via state/wave21-merge-corpus.py,
   then DELETE fragments).
2. Rewrite the 12 family routers with the new leaf rows; all descriptions
   ≤ 1024 chars (verify via state/wave16-router-desc-len.py).
3. README/DOMAINS/visuals reconciled to live counts + stale-number-guard
   R-N + N55/N56 fixtures (stale class = wave-20-close "294 leaf skills" /
   "602 tasks"; legit = wave-21 vocabulary). NOTE: Design v6 owns docs/*.svg
   and DESIGN.md — NEVER touch design files; if counts change visuals, run
   the generated visual pipeline per the repo's make visuals, but do NOT
   hand-edit design SVGs. G7 must stay green at HEAD.
4. Gates FRESH at final HEAD: make validate 5/5 (602+2N/602+2N) · make
   attest 3/3 · run-tests.sh ALL TESTS PASS (incl N55/N56 + N53/N54 +
   N49/N50 + G1-G8) · em dashes 0 skills/ · tree clean.
5. Push PRIVATE via GITHUB_TOKEN_ARJUN (fast-forward only) + ls-remote
   verify (remote == HEAD). NO Ashforde, NO visibility flip.
6. GROUP 160 post as self with SEND_EXIT=0 (bot DB receipt).
7. State note ops/automation/wave21-state.md (committed).

## STEP 5 — REPORT
Close-out text response ONLY after all of the above is done and verified.
Then relay CEO P5.2 WAVE-21 gate ≥9.5 → WAVE-22. No founder contact
(routine progress; balance topped up).
