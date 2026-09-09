# WAVE-48 LEAF PLAN — Aero Agent Skills P5.3 (recon complete 2026-09-09 ~11:15 CEST)

Baseline (verified at recon, HEAD 92d84a48): 645 leaves · 86 packs · 12
families · 1306 corpus tasks · 30 standards · ledger 645 rows.

## Recon summary (9 whole-family FRESH probes, receipts in ops/automation/state/wave48-recon/)

| task | family | verdict | receipt |
|---|---|---|---|
| 0 | flight-mechanics 49 | NO_CANDIDATES (saturated, 0 GO) | task-0-receipt.md |
| 1 | avionics 50 | 1 GO strong | task-1-receipt.md |
| 2 | propulsion 53 | 1 GO strong | task-2-receipt.md |
| 3 | gnc-autonomy 62 | 3 GO strong | task-3-receipt.md |
| 4 | vehicle-design 57 | 2 GO strong | task-4-receipt.md |
| 5 | structures 65 | 1 GO strong + 1 CONDITIONAL | task-5-receipt.md |
| 6 | systems-engineering-safety 47 (extension) | NO_CANDIDATES | task-6-receipt.md |
| 7 | manufacturing-quality 48 (extension) | NO_CANDIDATES | task-7-receipt.md |
| 8 | flight-test-operations 49 (extension) | NO_CANDIDATES | task-8-receipt.md |
| 9 | space-systems 52 (extension) | 1 GO strong | task-9-receipt.md |

Saturated re-probe order honored (SES -> MQ -> FTO -> SPACE). Pool after
extensions = 10 GO (9 strong + 1 conditional) >= the 10 viable floor; CC
56 / AERO 57 not re-probed (pool not below 10 after extensions — doctrine
stop). FM/SES/MQ/FTO declines STAND with fresh receipts.

## Planned leaves (10; smallest-first by family leaf count)

| # | leaf path | family (size) | source receipt | spec-time gate |
|---|---|---|---|---|
| 1 | avionics/fsw/cyclic-executive-scheduling | avionics 50 | task-1 | none — strong |
| 2 | space-systems/subsystems/mmod-shielding-sizing | space-systems 52 | task-9 | none — strong |
| 3 | propulsion/reciprocating/dual-cycle | propulsion 53 | task-2 | none — strong |
| 4 | vehicle-design/sizing/landing-gear-weight-estimation | vehicle-design 57 | task-4 | none — strong |
| 5 | vehicle-design/sizing/fuel-system-weight-estimation | vehicle-design 57 | task-4 | none — strong |
| 6 | gnc-autonomy/control/h-infinity-synthesis | gnc-autonomy 62 | task-3 | none — strong |
| 7 | gnc-autonomy/control/sliding-mode-control | gnc-autonomy 62 | task-3 | none — strong |
| 8 | gnc-autonomy/control/feedback-linearization | gnc-autonomy 62 | task-3 | none — strong |
| 9 | structures/composites/honeycomb-core-micromechanics | structures 65 | task-5 | none — strong |
| 10 | structures/composites/laminate-bending-stiffness | structures 65 | task-5 | CONDITIONAL — spec must fence B/D/unsymmetric synthesis as the ONLY claim; symmetric-A stays with laminate-stiffness; resolve the wave-47 micromechanics forbidden-token row by naming the consumer laminate-plate-buckling mis-attribution (wave-47 creep-stress-relaxation precedent landed at build) |

Family spread: avionics 1, space-systems 1, propulsion 1, vehicle-design
2, gnc-autonomy 3, structures 2 = 10 leaves across 6 families, 8 packs.
Every candidate is zero-owner tree-wide + zero in the 1306-task corpus +
sibling-fence-clear at recon HEAD (receipts carry verbatim fence quotes,
Hit@1 sim margins, zero-theft audits).

## Execution

1. Spec phase: batches <= 4 concurrent spec-engineer subagents, compact
   write-NOW prompts, anchor script FIRST with REAL anchor outputs, ONE
   format exemplar (state/wave47-specs/ conventions + _spec-engineer-kit
   if present). Commit specs INCREMENTALLY per batch.
2. Build rounds: Claude Code doer via ~/.hermes/scripts/aero-delegate.sh
   skills skill_build @<brief> --max-turns 40 --budget 10 (M1 routing;
   exit 1 DOER=DEEPSEEK -> DS daylight backup only; exit 3 investigate).
   3-4 concurrent builders max. leaf-create-gate BEFORE every commit (six
   artifacts; rate >= 9.5; ledger rows 646+; tests both interpreters; no
   exact-float asserts; portable imports; desc <= 1000 at draft).
   Rescue lane is the EXPECTED completion path (wave-46/47).
3. Close-out chain per wave48-brief.md step 5; gates FRESH at rest; push
   PRIVATE (GITHUB_TOKEN_ARJUN); publish-public.sh sanctioned sync; GROUP
   160 close-out post AS OPS MANAGER; wave48-state.md honest;
   products-state via aero-wave-state.sh close skills wave-48 <n> <ledger>
   <corpus>; spend record wave-build-48.

Mandate: land >= 10 verified leaves. Ledger target rows 646-655, corpus
1306 -> 1326.

Recon + plan committed by relay (orchestrator) 2026-09-09. Dispatch
authority: daylight CEO gate (10:00 CEST) — active.
