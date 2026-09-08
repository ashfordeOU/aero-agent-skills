# WAVE-47 BRIEF — Aero Agent Skills P5.2 (relay dispatch 2026-09-08 ~13:35 UTC)

Goal: land **+10-16 verified leaves, MUST land ≥10**, on the wave-46 close
baseline. Wave-46 CLOSED 2026-09-08 13:14 UTC (10 leaves, ledger 635, corpus
1286, public 8fa66b1, CI attest+release SUCCESS, state-note 1c37b416 pushed,
remote main == 1c37b416 == local HEAD). CEO cleared the stale HALT ~13:30 UTC
and assigned this dispatch to the relay (founder: "are you dispatching the
wave and following?").

## Baseline (verified at dispatch, HEAD 1c37b416)

**635 leaves · 86 packs · 12 families · 1286 router tasks · 30 standards**
(647 SKILL.md tracked = 635 leaves + 12 routers). Ratings ledger 635 rows
0 gap. Corpus eval/hit1-corpus.yaml = 1286.

Per-family leaf counts (docs/metrics.json, verified at HEAD this dispatch):
**systems-engineering-safety 47** · **flight-mechanics 48** ·
**manufacturing-quality 48** · **avionics 49** · **flight-test-operations
49** · **propulsion 52** · **space-systems 52** · **cross-cutting 56** ·
**vehicle-design 56** · **aerodynamics 57** · **gnc-autonomy 58** ·
**structures 63** (LARGEST).

## Probe strategy (RECEIPTS OVER LISTS, wave-46 doctrine)

Wave-46 recon ran WHOLE-FAMILY FRESH probes on all 12 families at 12:07-12:23
UTC TODAY with receipts in ops/automation/state/wave46-recon/ (HEAD then
45931c16; families unchanged since — wave-46 added leaves only to FM/AV/PROP/
GNC/VD/STRUCT). Per doctrine, saturated NO_CANDIDATES receipts STAND (declines
stand with receipts; nothing in those families changed). So wave-47 probes
FRESH only the families whose state CHANGED in wave-46 (new sibling fences =
new seams to check, zero-owner re-greps required):

1. **flight-mechanics 48** (+1 wave-46: rotorcraft-forward-flight-flapping)
   — probe FRESH whole family; rotorcraft performance/fwd-flight seams.
2. **avionics 49** (+1 wave-46: mixed-criticality-scheduling) — probe FRESH;
   fsw/do178c scheduling + do254/data-bus seams (TAWS/GPWS/Mode-S stay CLOSED).
3. **propulsion 52** (+2 wave-46: hydrogen-peroxide, piston-engine-cycle; NEW
   pack reciprocating) — probe FRESH; scramjet CLOSED definitively; clean
   closed-form/station-level producers only.
4. **gnc-autonomy 58** (+3 wave-46) — probe FRESH navigation/optimal-control/
   estimation/guidance veins.
5. **vehicle-design 56** (+1 wave-46: landing-gear-height-sizing) — probe only
   if pool < ~12 after 1-4 exhaust (extension tier).
6. **structures 63** (+2 wave-46) — probe only if pool < ~12 (extension tier,
   LARGEST family).

Saturated families (SES 47, MQ 48, FTO 49, SPACE 52, CC 56, AERO 57): wave-46
whole-family NO_CANDIDATES receipts STAND — do NOT re-probe unless the viable
pool sits below ~10 after extensions (then probe smallest-first with receipts).

## Plan decision rule

Build from fresh probe receipts, smallest-first. Target 12-16 planned; viable
pool ≥10 required. If the pool drops below ~12, EXTEND to vehicle-design 56 →
structures 63 → then re-probe smallest saturated (SES 47 → MQ 48 → FTO 49)
with fresh whole-family receipts. Wave-46 precedent: extensions restored the
pool when primary sat below viability.

## Execution pattern (wave-46 doctrine, wave-39..46 hardened)

1. Probes: ≤5 parallel read-only probe subagents, whole-family FRESH for the
   families above, RECEIPTS OVER LISTS — written receipts with decline
   reasons, saved to ops/automation/state/wave47-recon/. NO candidates from
   memory. Receipts MUST NOT quote machine-local absolute paths (publish-
   public.sh tripwire — sanitize to portable form at write time).
2. Write state/wave47-leaf-plan.md (candidates, receipts cited, family
   spread, plan size 12-16). Commit recon + leaf plan (explicit paths).
3. Spec phase: batches ≤4 concurrent spec-engineer subagents, compact
   write-NOW prompts, anchor script FIRST with REAL anchor outputs, ONE
   format exemplar (state/wave46-specs/ files + _spec-engineer-kit.md).
   Spec prose MUST match anchor math; all specs em-dash-free, desc ≤ limits,
   standards ids in standards-map. Commit specs INCREMENTALLY per batch.
4. Build rounds: Claude Code doer via `~/.hermes/scripts/aero-delegate.sh
   skills skill_build @<brief> --max-turns 40 --budget 10` (M1 routing).
   Delegate exit 0 = claude ran; exit 1 = DOER=DEEPSEEK → run that unit as a
   DeepSeek subagent backup ONLY in daylight; exit 3 = unexpected gate
   refusal → investigate. 3-4 concurrent builders max. leaf-create-gate
   BEFORE every commit (six artifacts: SKILL.md + logic + contract test +
   eval fragment + hit1 yaml + ledger row), rate-at-creation ≥9.5, ledger
   rows 636+. Tests pass under BOTH interpreters; no exact-float equality
   asserts; contract tests MUST NOT use machine-local sys.path;
   __pycache__ purge before gates; desc ≤1000 chars/148 words at draft.
   Delegate NEVER pushes — gates + push + publish stay with the orchestrator.
5. Close-out chain (in order): pre-merge sim (zero thefts) → corpus merge
   1286 + 2N → delete fragments → family routers (+rows, +guidance bullets,
   parity == leaves, descs ≤1024) → make visuals → **gates FRESH at rest**:
   make validate PASS 5/5 · make attest PASS 3/3 · make completeness ALL
   REQUIRED PASS · make value-delta PASS · make visuals-check PASS · make
   manifest-check PASS · router descs ≤1024 · stale-number-guard · em dashes
   0 in skills/ · git status clean → push PRIVATE (GITHUB_TOKEN_ARJUN only,
   token-in-URL) → ls-remote verify remote main == HEAD → publish-public.sh
   sanctioned sync (leaf-count guard; NO force; NO direct ashfordeOU push)
   → record ACTUAL public commit (hourly automation may race ahead — verify
   CI attest + release-on-milestone on ACTUAL public HEAD) → GROUP 160
   close-out post AS OPS MANAGER (own profile bot) → wave47-state.md honest
   (receipts, disclosures) → **update products-state via
   `~/.hermes/scripts/aero-wave-state.sh close skills wave-47 <n> <ledger> <corpus>`
   (FIX 2026-09-08: stale HALT blocked wave-47 dispatch for hours — the
   close-out MUST update state itself, never leave it for manual
   handoff)** → commit + push.
6. Final report: concise block (leaves landed, gates, pushes, public HEAD,
   disclosures, actual spend). Record spend:
   `python3 ~/.hermes/scripts/run_budget.py record --job wave-build-47 --usd <actual>`.

## Budget

wave-build cap $20 (run_budget.py check exit 0 at dispatch: est $18).
Relay cap $5 does not apply to the build itself.

## Hard rules

- **TURN-ALIVE**: never end the turn with a text-only response until the
  final close-out report — a text yield mid-delegation kills the session's
  children (wave-44 lesson). Use sleep-poll + real tool calls between
  delegations.
- QH gate exit 0 before EVERY DS batch
  (`python3 ~/.hermes/scripts/quiet-hours-gate.py --check`). Started ~13:35
  UTC — ~6h daylight to 19:30 UTC guard; a full wave ≈3-3.5h, close well
  before the guard. If anything slips toward the window, stop cleanly and
  queue the remainder for the night executor (staged briefs, claude doer).
- ONE wave at a time. No duplicates. Sibling ticks see tree dirty = in
  flight (this brief committed immediately = in-flight marker).
- NO direct push to ashfordeOU — publish only via publish-public.sh after
  the private push lands (publish law).
- No founder contact mid-wave. GROUP 160 post only at close-out.
- Record actuals honestly in wave47-state.md — disclosures over silence.

Relay dispatch 2026-09-08 ~13:35 UTC — first wave dispatched by the relay
after CEO HALT-clear (wave-46 was CEO-lane). Baseline 635, mandate ≥10.
