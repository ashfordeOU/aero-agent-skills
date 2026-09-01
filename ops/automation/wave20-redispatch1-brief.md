# WAVE-20 REDISPATCH #1 — AeroSkills build (TURN-ALIVE hard fix)

Source: relay CEO 2026-09-01 ~18:55 UTC. Prior proc 69210 died 20:35:28 CEST
(TURN-ALIVE violation #3) with ZERO leaf commits — see step 0. Baseline:
HEAD f956b8b (wave-20 brief), 282 leaves + 12 routers = 294 SKILL.md,
corpus 578, ratings ledger 282 rows, em dashes 0. Remote main == 6716069
(push deferred per CI-first — correct).

## STEP 0 — TURN-ALIVE (HARD, 3rd occurrence — this is the reason you exist)
The previous run died because the bot wrote a **text response** ("Batch 1 is
in flight...") while 4 async delegations were LIVE. A text response ENDS the
turn and the CLI tears down live delegations ("Interrupted 1 async
delegation(s) (CLI shutdown)" + interrupted_during_api_call). Same class as
wave-16 original and wave-19 original.

HARD RULES:
1. **NEVER write your final text response while any delegation is live.**
   The ONLY text response is the close-out, AFTER every subagent has
   completed AND you have verified their commits.
2. If you want to report status mid-build, post to GROUP 160 via the
   `hermes send` TOOL (a tool call) — never via a text response.
3. Stay alive by POLLING with tool calls: check delegation status
   (process/task-log checks, git log, `ps`), keep issuing tool calls until
   ALL subagents complete. Do not end the turn early.
4. If the CLI is externally killed mid-wave: resume from committed leaves
   only — incremental commits are the only durable record.

## STEP 1 — API HEALTH FIRST
Check DeepSeek API health (429/402). If degraded → build SEQUENTIALLY,
one leaf at a time, commit each immediately, NO fan-out; re-test every 3
leaves. Fan-out ONLY if healthy, CAP 3-4 concurrent subagents (API limit 5).
If balance exhausted → STOP CLEAN: state note "BALANCE BLOCKED — founder
must top up DeepSeek", NO fake gates, no founder contact beyond the note.

## STEP 2 — FAN-OUT (ONE SUBAGENT PER SKILL)
Target +10-16 verified leaves, MUST land ≥10. Family order:
six 23-count families FIRST: flight-mechanics → gnc-autonomy → propulsion →
space-systems → systems-engineering-safety → vehicle-design.
Then 24-count if headroom: aerodynamics → avionics → cross-cutting →
flight-test-operations → structures → manufacturing-quality.
Each subagent builds ONE leaf: brainstorm (Superpowers) → SKILL.md +
scripts/ contract test + 2 corpus tasks + standards-map ext → make validate
green → rate ≥9.5 in eval/skill-ratings.md IN THE SAME BUILD TURN (rebuild
in-turn if below; leaf not done until rated) → commit own leaf (7-rule).

## STEP 3 — GIT-RACE MITIGATION (hard)
Subagents commit EXPLICIT PATHS ONLY: own leaf dir + own eval fragment +
eval/skill-ratings.md. NEVER `git add -A` / `git add .` / `git reset`.
Index-lock → retry with backoff.

## STEP 4 — CONCURRENT DESIGN SESSION (NEW — do not fight it)
A main-profile session owns AeroSkills design files (docs/banner.svg,
docs/domain-map.svg, README design). It is ACTIVE NOW and may commit
docs changes mid-wave. Rules:
- NEVER edit docs/banner.svg, docs/domain-map.svg, or docs/DESIGN.md.
- If G7 (stale-number guard) goes red because the design session pushed
  stale counts: DO NOT edit those docs yourself. Note it in your state and
  report at close-out — the CEO handles design-stream gate fixes.
- Your gates run on YOUR leaves; the design session's docs are its owner's
  problem. Keep your own commits clean and explicit.

## STEP 5 — CLOSE-OUT (after ≥10 leaves committed)
1. Corpus merge: 578 → 578+2N tasks + delete all wave-20 eval fragments.
2. Router rewrites ≤1024 (canonical wave16-router-desc-len.py).
3. README badge → 282+N + N53/N54 guard fixtures (legit + stale classes).
4. Gates FRESH: make validate 5/5 · make attest 3/3 · run-tests.sh ALL PASS
   (incl N53/N54 + N49/N50 + G7) · em dashes 0 skills/ · tree clean.
5. Push PRIVATE: GITHUB_TOKEN_ARJUN → arjun-0077/aeroskills + ls-remote
   verify. PUBLISH LAW: NO Ashforde, NO public — ever.
6. GROUP 160 post as self (SEND_EXIT=0 verified).
7. State note ops/automation/wave20-state.md committed.
8. ONLY NOW write your final text response (close-out summary with receipts).

## ACCEPTANCE (for CEO gate)
≥10 leaves rated 9.5 in-turn · corpus 578+2N · routers ≤1024 · badge +
N53/N54 · gates FRESH replay green · push ls-remote-verified (private) ·
GROUP 160 post SEND_EXIT=0 · wave20-state.md · tree clean.
