# WAVE-48 BRIEF — Aero Agent Skills P5.3 (staged 2026-09-08 ~22:50 CEST for 10:00 daylight gate)

Goal: land **+10-16 verified leaves, MUST land ≥10**, on the wave-47 close
baseline. Wave-47 CLOSED 2026-09-08 (10 leaves, ledger 645, corpus 1306,
public 47f8173c, CI attest+release SUCCESS). This brief is STAGED during
quiet hours per the quiet-for-ALL ruling — planning only. The daylight CEO
gate (10:00 CEST = 08:00 UTC) dispatches it; no build happens before that
gate.

## Baseline (verified at stage time, HEAD 94639bc3)

**645 leaves · 86 packs · 12 families · 1306 router tasks · 30 standards**
(657 SKILL.md tracked = 645 leaves + 12 routers). Ratings ledger 645 rows
0 gap. Corpus eval/hit1-corpus.yaml = 1306.

Per-family leaf counts (docs/metrics.json, verified at stage HEAD):
**flight-mechanics 49** · **avionics 50** · **manufacturing-quality 48** ·
**flight-test-operations 49** · **propulsion 53** · **space-systems 52** ·
**cross-cutting 56** · **vehicle-design 57** · **aerodynamics 57** ·
**gnc-autonomy 62** · **structures 65** (LARGEST) ·
**systems-engineering-safety 47** (SMALLEST).

## Probe strategy (RECEIPTS OVER LISTS, wave-46/47 doctrine)

Wave-47 recon receipts are on file in ops/automation/state/wave47-recon/:
task-6 CC NO_CANDIDATES · task-7 SES NO_CANDIDATES · task-8 MQ
NO_CANDIDATES · task-9 FTO NO_CANDIDATES (whole-family FRESH, HEAD
1c37b416). Per doctrine, those decline-with-receipts STAND unless the
family changed since. Wave-47 added leaves to FM/AV/PROP/VD/GNC/STRUCT —
those six have new sibling fences and need FRESH whole-family probes:

1. **flight-mechanics 49** (+1 wave-47: rotorcraft-cyclic-pitch-trim) —
   probe FRESH whole family; rotorcraft + performance seams.
2. **avionics 50** (+1 wave-47: virtual-deadline-scheduling) — probe FRESH;
   fsw scheduling + do254/data-bus seams (TAWS/GPWS/Mode-S stay CLOSED).
3. **propulsion 53** (+1 wave-47: diesel-cycle) — probe FRESH;
   reciprocating/station-level producers only; scramjet CLOSED.
4. **gnc-autonomy 62** (+4 wave-47) — probe FRESH navigation/guidance/
   control/estimation veins (most wave-47 growth here = most seams).
5. **vehicle-design 57** (+1 wave-47: component-weight-estimation) —
   probe FRESH; sizing/weight/landing-gear seams.
6. **structures 65** (+2 wave-47) — probe FRESH (LARGEST family, extension
   tier if pool < ~12 after 1-5).

Saturated with standing receipts (CC 56, SES 47, MQ 48, FTO 49, SPACE 52,
AERO 57): do NOT re-probe unless the viable pool sits below ~10 after
extensions (then probe smallest-first: SES 47 → MQ 48 → FTO 49 → SPACE 52
→ CC 56 → AERO 57, fresh receipts each).

## Plan decision rule

Build from fresh probe receipts, smallest-first among fertile families.
Target 12-16 planned; viable pool ≥10 required. If the pool drops below
~12, EXTEND: structures 65 → then smallest saturated with fresh receipts
(SES 47 → MQ 48 → FTO 49). Wave-46/47 precedent: extensions restored the
pool when primaries sat below viability.

## Execution pattern (wave-46/47 doctrine, hardened across 39-47)

1. Probes: ≤5 parallel read-only probe subagents, whole-family FRESH for
   families above, receipts with decline reasons → ops/automation/state/
   wave48-recon/. NO candidates from memory. Receipts MUST NOT quote
   machine-local absolute paths (publish tripwire — sanitize at write).
2. Write state/wave48-leaf-plan.md (candidates, receipts cited, family
   spread, plan size 12-16). Commit recon + leaf plan (explicit paths).
3. Spec phase: batches ≤4 concurrent spec-engineer subagents, compact
   write-NOW prompts, anchor script FIRST with REAL anchor outputs, ONE
   format exemplar (state/wave47-specs/ + _spec-engineer-kit.md). Spec
   prose MUST match anchor math; em-dash-free, desc ≤ limits, standards
   ids in standards-map. Commit specs INCREMENTALLY per batch.
4. Build rounds: Claude Code doer via ~/.hermes/scripts/aero-delegate.sh
   skills skill_build @<brief> --max-turns 40 --budget 10 (M1 routing).
   Delegate exit 0 = claude ran; exit 1 = DOER=DEEPSEEK → DS backup ONLY
   in daylight; exit 3 = gate refusal → investigate. 3-4 concurrent
   builders max. leaf-create-gate BEFORE every commit (six artifacts:
   SKILL.md + logic + contract test + eval fragment + hit1 yaml + ledger
   row), rate-at-creation ≥9.5, ledger rows 646+. Tests pass BOTH
   interpreters; no exact-float equality asserts; no machine-local
   sys.path; __pycache__ purge; desc ≤1000 chars at draft. Delegate NEVER
   pushes.
5. Close-out chain (in order): pre-merge sim (zero thefts) → corpus merge
   1306 + 2N → delete fragments → family routers (+rows, +guidance,
   parity == leaves, descs ≤1024) → make visuals → gates FRESH at rest:
   make validate 5/5 · attest 3/3 · completeness ALL REQUIRED · value-delta
   · visuals-check · manifest-check · router descs ≤1024 ·
   stale-number-guard · em dashes 0 in skills/ · git clean → push PRIVATE
   (GITHUB_TOKEN_ARJUN only) → ls-remote verify → publish-public.sh
   sanctioned sync (leaf-count guard, no force) → record ACTUAL public
   commit (hourly automation may race; verify CI on ACTUAL public HEAD) →
   GROUP 160 close-out post AS OPS MANAGER → wave48-state.md honest →
   update products-state via ~/.hermes/scripts/aero-wave-state.sh close
   skills wave-48 <n> <ledger> <corpus> → commit + push.
6. Final report: concise block (leaves landed, gates, pushes, public HEAD,
   disclosures, actual spend). Record spend:
   python3 ~/.hermes/scripts/run_budget.py record --job wave-build-48 --usd <actual>.

## Budget

wave-build cap $20 (run_budget.py check exit 0 at dispatch). Relay cap
does not apply to the build itself.

## Hard rules

- **TURN-ALIVE**: never end the turn text-only until the final close-out —
  a text yield mid-delegation kills the session's children (wave-44
  lesson). Sleep-poll + real tool calls between delegations.
- QH gate exit 0 before EVERY DS batch. Dispatch at 10:00 CEST = full
  daylight to ~20:00 UTC guard; a full wave ≈3-3.5h, close well before.
  If it slips toward the window, stop cleanly and queue the remainder
  (staged briefs, claude doer).
- ONE wave at a time. No duplicates. This committed brief = in-flight
  marker from the moment the daylight gate dispatches.
- NO direct push to ashfordeOU — publish only via publish-public.sh.
- No founder contact mid-wave. GROUP 160 post only at close-out.
- Record actuals honestly in wave48-state.md — disclosures over silence.

Staged 2026-09-08 ~22:50 CEST by Arjun (CEO) per founder directive — plan
ahead so 10:00 tomorrow fires straight into execution. Baseline 645,
mandate ≥10. Dispatch authority: daylight CEO gate 2026-09-09 10:00 CEST.
