# WAVE-49 BRIEF — Aero Agent Skills P5.3 (staged 2026-09-09 ~11:45 UTC for immediate daylight gate)

Goal: land **+10-16 verified leaves, MUST land ≥10**, on the wave-48 close
baseline. Wave-48 CLOSED 2026-09-09 11:36 UTC (10 leaves, ledger 655,
corpus 1326, private 5b112816 pushed+verified, public f6a3d8c1 CI
attest+release SUCCESS). Daylight dispatch same tick as staging; night
model REVERSED holds — no night execution, executor PAUSED.

## Baseline (verified at stage time, HEAD 5b112816, tree clean)

**655 leaves · 86 packs · 12 families · 1326 router tasks · 30 standards**
(667 SKILL.md tracked = 655 leaves + 12 routers). Ratings ledger 655 rows
contiguous. Corpus eval/hit1-corpus.yaml = 1326. Gates FRESH at rest at
close: validate 5/5 · attest 3/3 · completeness · value-delta 10/10 ·
visuals · parity · em-dash 0 · stale-number-guard.

Per-family leaf counts (docs/metrics.json, verified at stage HEAD):
**flight-mechanics 49** · **avionics 51** · **manufacturing-quality 48** ·
**flight-test-operations 49** · **propulsion 54** · **space-systems 53** ·
**cross-cutting 56** · **vehicle-design 59** · **aerodynamics 57** ·
**gnc-autonomy 65** · **structures 67** (LARGEST) ·
**systems-engineering-safety 47** (SMALLEST).

## Probe strategy (RECEIPTS OVER LISTS, wave-46/47/48 doctrine)

Wave-48 recon receipts are on file in ops/automation/state/wave48-recon/
(task-0..9, whole-family FRESH at HEAD 92d84a48). Per doctrine, wave-48
declines STAND unless the family changed since. Wave-48 added leaves to
AV/SPACE/PROP/VD/GNC/STRUCT — those six have NEW sibling fences and need
FRESH whole-family probes:

1. **gnc-autonomy 65** (+3 wave-48: h-infinity-synthesis,
   sliding-mode-control, feedback-linearization) — probe FRESH;
   nonlinear/robust-adaptive seams were its growth; check what the three
   new leaves fence out (variable-structure now landed → what is still
   zero-owner: e.g. L1-adaptive, backstepping, mu-synthesis re-verify
   FRESH, estimation/navigation veins).
2. **vehicle-design 59** (+2 wave-48: landing-gear-weight-estimation,
   fuel-system-weight-estimation) — probe FRESH; sizing/weight seams.
3. **structures 67** (+2 wave-48: honeycomb-core-micromechanics,
   laminate-bending-stiffness) — probe FRESH (LARGEST family; extension
   tier if pool < ~12 after 1-5).
4. **avionics 51** (+1 wave-48: cyclic-executive-scheduling) — probe
   FRESH; fsw scheduling + do254/data-bus seams (TAWS/GPWS/Mode-S stay
   CLOSED).
5. **propulsion 54** (+1 wave-48: dual-cycle) — probe FRESH;
   reciprocating/station-level producers only; scramjet CLOSED.
6. **space-systems 53** (+1 wave-48: mmod-shielding-sizing — first SPACE
   GO since wave-46, genuinely new seam) — probe FRESH; the seam that
   reopened SPACE may have siblings (batch 2 slot, after pool from 1-5
   known).

Standing NO_CANDIDATES with FRESH wave-48 receipts (FM 49, SES 47, MQ 48,
FTO 49): do NOT re-probe unless the viable pool sits below ~10 after 6
(then probe smallest-first: SES 47 → MQ 48 → FM 49 → FTO 49 → CC 56 →
AERO 57, fresh receipts each). CC/AERO not FRESH-probed in wave-48 —
standing receipts only; probe last if pool still short.

## Plan decision rule

Build from fresh probe receipts, smallest-first among fertile families.
Target 12-16 planned; viable pool ≥10 required. If the pool drops below
~12, EXTEND: structures 67 → then smallest saturated with fresh receipts
(SES 47 → MQ 48 → FM 49 → FTO 49). Wave-46/47/48 precedent: extensions
restored the pool when primaries sat below viability.

## Execution pattern (wave-46/47/48 doctrine, hardened across 40-48)

1. Probes: ≤5 parallel read-only probe subagents per batch, whole-family
   FRESH for families above, receipts with decline reasons →
   ops/automation/state/wave49-recon/. NO candidates from memory.
   Receipts MUST NOT quote machine-local absolute paths (publish
   tripwire — sanitize at write).
2. Write state/wave49-leaf-plan.md (candidates, receipts cited, family
   spread, plan size 12-16). Commit recon + leaf plan (explicit paths).
3. Spec phase: batches ≤4 concurrent spec-engineer subagents, compact
   write-NOW prompts, anchor script FIRST with REAL anchor outputs, ONE
   format exemplar (state/wave48-specs/ + _spec-engineer-kit.md). Spec
   prose MUST match anchor math; em-dash-free, desc ≤ limits, standards
   ids in standards-map. Commit specs INCREMENTALLY per batch.
4. Build rounds: Claude Code doer via ~/.hermes/scripts/aero-delegate.sh
   skills skill_build @<brief> --max-turns 40 --budget 10 (M1 routing).
   Delegate exit 0 = claude ran; exit 1 = DOER=DEEPSEEK → DS backup ONLY
   in daylight; exit 3 = gate refusal → investigate. 3-4 concurrent
   builders max. EXPECTED: Claude builders hit the 40-turn cap pre-commit
   (wave-48: 10/10) — the DS daylight rescue lane is the STANDARD
   completion path: orchestrator PRE-APPENDS ratings ledger rows before
   each rescue batch (wave-48 lesson: no row gaps), then rescue agents
   complete artifacts, run leaf-create-gate (exit 0), commit.
   leaf-create-gate BEFORE every commit (six artifacts: SKILL.md + logic
   + contract test + eval fragment + hit1 yaml + ledger row),
   rate-at-creation ≥9.5. Tests pass BOTH interpreters; no exact-float
   equality asserts; no machine-local sys.path; __pycache__ purge; desc
   ≤1000 chars at draft. Delegate NEVER pushes.
5. Close-out chain (in order): pre-merge sim (zero thefts) → corpus merge
   1326 + 2N → delete fragments → family routers (+rows, +guidance,
   parity == leaves, descs ≤1024) → make visuals → gates FRESH at rest:
   make validate 5/5 · attest 3/3 · completeness ALL REQUIRED · value-delta
   · visuals-check · manifest-check · router descs ≤1024 ·
   stale-number-guard · em dashes 0 in skills/ · git clean → push PRIVATE
   (GITHUB_TOKEN_ARJUN only) → ls-remote verify → publish-public.sh
   sanctioned sync (leaf-count guard, no force) → record ACTUAL public
   commit (hourly automation may race; verify CI on ACTUAL public HEAD) →
   GROUP 160 close-out post AS OPS MANAGER → wave49-state.md honest →
   update products-state via ~/.hermes/scripts/aero-wave-state.sh close
   skills wave-49 <n> <ledger> <corpus> → commit + push.
6. Final report: concise block (leaves landed, gates, pushes, public HEAD,
   disclosures, actual spend). Record spend:
   python3 ~/.hermes/scripts/run_budget.py record --job wave-build-49 --usd <actual>.

## Budget

wave-build cap $20 (run_budget.py check exit 0 at dispatch: est $2.00 <=
$20.00 OK). Relay cap does not apply to the build itself. Recon probes +
spec engineers + rescue agents at documented deepseek-v4-flash rates
(~$0.01-0.03 each); Claude Code doer runs on Max subscription (~$0).

## Hard rules

- **TURN-ALIVE**: never end the turn text-only until the final close-out —
  a text yield mid-delegation kills the session's children (wave-44
  lesson). Sleep-poll + real tool calls between delegations.
- QH gate exit 0 before EVERY DS batch. Full daylight now (~11:45 UTC);
  a full wave ≈3-3.5h, close well before 20:00 UTC guard. If it slips
  toward the window, stop cleanly and queue the remainder (staged briefs,
  claude doer).
- ONE wave at a time. No duplicates. This committed brief = in-flight
  marker from the moment the daylight gate dispatches.
- NO direct push to ashfordeOU — publish only via publish-public.sh.
- No founder contact mid-wave. GROUP 160 post only at close-out.
- Record actuals honestly in wave49-state.md — disclosures over silence.

Staged + dispatched 2026-09-09 ~11:45 UTC by Arjun (CEO) per wave-48
close handoff ("Next: wave-49 planning at CEO gate"). Baseline 655,
mandate ≥10. Dispatch authority: daylight CEO gate 2026-09-09 11:45 UTC.
