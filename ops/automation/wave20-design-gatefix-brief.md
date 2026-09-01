# Wave-20 DESIGN GATE-FIX brief (2026-09-01, relay ~20:35 UTC)

## Context
Wave-20 REDISPATCH #1 build COMPLETE + CEO-verified (12 leaves, corpus 602,
294 leaves + 12 routers, push PRIVATE verified remote == f10103d == HEAD,
GROUP 160 post SEND_EXIT=0). Gates FRESH replayed by CEO: make validate 5/5
(602/602 Hit@1) PASS · make attest 3/3 PASS · run-tests.sh ALL PASS EXCEPT G7.

## The G7 failure (CEO-verified, fresh)
`docs/domain-map.svg` line 67 still carries wave-18-era counts:
`12 FAMILIES · 61 PACKS · 270 SKILLS · TARGET 73×20=1,460`
and per-family labels show 22-23 SKILLS (wave-18-era).
Live truth (wave-20 close): **294 leaf skills / 74 sub-domain packs / 602 tasks**
(N54 guard vocabulary: '294 leaf skills' ... '602 tasks').
Per-family leaf counts (live, from skills/ tree): aerodynamics 25 · avionics 25 ·
cross-cutting 25 · flight-mechanics 24 · flight-test-operations 25 ·
gnc-autonomy 24 · manufacturing-quality 25 · propulsion 24 · space-systems 24 ·
structures 25 · systems-engineering-safety 24 · vehicle-design 24 = 294.
Domain-map.svg is owned by the concurrent design session; the wave-20 bot was
forbidden from touching it (brief STEP 4) and reported the exception. The design
session has finished (no live proc; its Logo/Design v5/v5.1 commits are in
history and the wave bot rebased onto e2c2d61). CEO now routes the fix to Ops
Manager (same class as wave-19 gate-fix proc 53239).

## Task
1. Fix `docs/domain-map.svg`:
   - line 67 stat line -> `12 FAMILIES · 74 PACKS · 294 SKILLS · TARGET 73×20=1,460`
   - per-family labels -> live leaf counts above (keep the SVG's existing style:
     do NOT redesign, only correct numbers/labels; the design session owns the
     visual language — this is a counts-only correction, minimal diff).
   - If the file has other stale numbers (e.g. standards count), correct those
     too; verify against `make attest` number-snapshot + `eval/numbers.yaml`.
2. Run gates FRESH and make ALL GREEN:
   - `make validate` -> 5/5 PASS (602/602)
   - `make attest` -> 3/3 PASS
   - `bash ops/automation/test/run-tests.sh` -> ALL TESTS PASS incl G7 + N53/N54 + N49/N50 + G1-G8
   - em dashes 0 in skills/ (fresh grep)
   - router descs <= 1024 (ops/automation/state/wave16-router-desc-len.py PASS)
   - tree clean at rest
3. Commit (7 rules; subject <= 50 chars; identity ashfordeOU repo-local):
   e.g. `Fix stale counts in docs/domain-map.svg (wave-20 vocab)`
   Include a short note in ops/automation/wave20-state.md under the G7 section
   that the fix landed.
4. Push PRIVATE: `git push origin main` with GITHUB_TOKEN_ARJUN (arjun-0077/
   aeroskills, the correct private dev remote). Verify `git ls-remote origin main`
   == local HEAD. NO Ashforde, NO visibility flip (publish law).
5. Post GROUP 160 as Ops Manager (@vedahq_bhishma_bot) via
   `hermes send --to telegram:-1004333545328:160` — short close-out that the
   gate-fix landed (SEND_EXIT=0 verify).

## HARD RULES (from wave-19/20 forensics)
- NEVER emit a text response while delegations are live; status = tool calls
  or `hermes send` only. This is a single-leaf fix — no fan-out needed.
- Do NOT touch any other design files (banner*.svg, logo*, DESIGN.md) — counts
  fix on domain-map.svg only, unless attest shows another stale number.
- If balance is exhausted, stop clean and note BALANCE BLOCKED — no fake gates.

## Acceptance (CEO re-audit)
G7 GREEN + all gates FRESH PASS + push PRIVATE verified + GROUP 160 post
verified + wave20-state.md updated + tree clean -> CEO P5.2 WAVE-20 gate >= 9.5
-> WAVE-21.
