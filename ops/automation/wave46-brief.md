# WAVE-46 BRIEF — Aero Agent Skills P5.2 (CEO dispatch 2026-09-07 ~12:30 UTC)

Goal: land **+10-16 verified leaves, MUST land ≥10**, on the wave-45 close
baseline.

## Baseline (verified at dispatch, HEAD dc9fba48)

Wave-45 CLOSE + CEO audit PASSED 9.66/10 (2026-09-07 ~12:25 UTC, fresh CEO
replay at rest: make validate PASS 5/5 1266/1266 Hit@1 · attest 3/3 ·
completeness ALL PASS · value-delta 10/10 ≥0.2 · visuals-check PASS 19
artifacts · manifest-check PASS · ledger 625 rows contiguous · em dashes 0 ·
tree clean at close; private remote == dc9fba48 == HEAD then, public
6e2bcb69 with CI attest SUCCESS + release-on-milestone SUCCESS). Post-close
local commit **4eee88f7 "sanitize internal refs from wave briefs + runbooks
(review gate follow-up)" is a sibling review-gate sanitize commit** (ops
docs only — chat IDs → <CHAT_ID>, profile paths → env pattern; NO skill
content, metrics.json unchanged, carries with the next push per wave-45
precedent 5fb0c13e):

**625 leaves · 85 packs · 12 families · 1266 router tasks · 30 standards**
(637 SKILL.md tracked = 625 leaves + 12 routers). Ratings ledger 625 rows
0 gap. Corpus eval/hit1-corpus.yaml = 1266.

Per-family leaf counts (docs/metrics.json, verified at HEAD this dispatch):
**flight-mechanics 47** · **systems-engineering-safety 47** ·
**avionics 48** · **manufacturing-quality 48** · **flight-test-operations
49** · **propulsion 50** · **space-systems 52** · **gnc-autonomy 55** ·
**vehicle-design 55** · **cross-cutting 56** · **aerodynamics 57** ·
**structures 61** (LARGEST).

## Smallest-first candidate order (probe FRESH, RECEIPTS OVER LISTS)

1. **flight-mechanics 47 (TIED SMALLEST — wave-45 whole-family probe
   NO_CANDIDATES with receipts; wave-43 declines stood (rotorcraft-height-
   velocity-diagram ANALYSIS vs FTO measurement slot, rotorcraft-forward-
   flight-envelope-limits fabricated-table risk); NOT saturated — revisit
   FRESH: fixed-wing + rotorcraft performance-mechanics gaps, clean closed-
   form only; expect few/0.**
2. **systems-engineering-safety 47 (SATURATED reaffirmed FRESH wave-45:
   NO_CANDIDATES with receipts — all six ARP4761A process functions exist;
   reliability-prediction-parts-count CLOSED (no MIL-HDBK-217/Telcordia id
   in standards-map). Probe only clean determinism, expect 0.**
3. **avionics 48 (yielding: wave-45 +1 deadline-monotonic-scheduling
   (fsw/do-178c); probe whole family FRESH; TAWS/GPWS + Mode-S stay CLOSED
   (wave-32 decline, RTCA-gated, no standards-map id); do178c/do254/do160/
   fsw/flight-management/data-bus seams, receipts over lists.**
4. **manufacturing-quality 48 (SATURATED reaffirmed FRESH wave-45: NO_
   CANDIDATES with receipts; CMM seam standards-map-blocked. Probe only
   clean determinism, expect 0.**
5. **flight-test-operations 49 (yielding: wave-45 +1 vmcl-determination;
   measurement-side seam (wave-42 13/14 saturation → wave-43 +3 → wave-44
   +1 → wave-45 +1) is thinning; probe whole family FRESH — envelope +
   performance measurement/planning gaps, clean deterministic only.**
6. **propulsion 50 (yielding: wave-45 +2 mpd-thruster (electric) +
   hydrazine-monopropellant-thruster (rocket); scramjet CLOSED DEFINITIVELY
   (do NOT re-open); wave-39/43/44 declines stood (drag loss, PPT,
   resistojet, pressurant, ablative, turboshaft/engine-matching/axial-
   stage); probe FRESH with receipts, only clean closed-form/station-level
   producers.**
7. **space-systems 52 (SATURATED reaffirmed FRESH wave-45: NO_CANDIDATES
   with receipts; CCSDS 131.0-B seam map-blocked. Probe only clean
   determinism, expect 0.**
8. **gnc-autonomy 55 (NOT saturated — yielded 5 straight waves incl
   wave-45 +3 loop-transfer-recovery/l1-adaptive-control/cramer-rao-lower-
   bound; probe navigation/optimal-control/estimation/guidance veins
   FRESH; tdoa-positioning fence re-check vs manufacturing-quality
   acoustic-emission before opening.**
9. **vehicle-design 55 (largest-last tier; wave-45 extension probe NO_
   CANDIDATES with receipts; probe only if the viable pool sits below ~12
   after smaller families exhaust.**
10. **cross-cutting 56 (default CLOSED — but wave-45 extension DID yield
    fir-bandpass-bandstop-filter-design under the pool-drop rule; probe
    numerics/sep2640/tolerancing only if every smaller family is provably
    exhausted.**
11. **aerodynamics 57 (dense receipt — NINE straight waves incl wave-45
    +4 sears-function-gust-lift/squire-young-profile-drag/laminar-far-wake/
    mangler-axisymmetric-transform; wave-41/43 declines stood (SWBLI/real-
    gas/hypersonic-viscous-interaction/tangent-wedge/supersonic-linearized-
    theory); probe FRESH only clean closed-form gaps in high-speed/
    boundary-layer/aeroelasticity veins.**
12. **structures 61 (LARGEST — probe last; wave-43/44/45 reserves now
    USED (statically-indeterminate, restrained-warping, inelastic-column-
    buckling, walker-forman-crack-growth); clean solid-mechanics/instability
    gaps only if every smaller family is provably exhausted.**

## Plan decision rule

Build from the fresh probe receipts in the order above (smallest-first).
Target 12-16 planned; viable pool ≥10 required. If the smaller-family pool
drops below ~12 with spec-time triage, EXTEND probes to vehicle-design 55 →
structures 61 → cross-cutting 56 (read sibling fences, receipts over lists)
— wave-45 precedent: extension probe (3 read-only agents) restored the pool
from 12 to 15.

## Wave-46 execution pattern (per wave doctrine, wave-39..45 hardened)

1. Read this brief + builder kit + close runbook (from the wave-45 kit in
   state/ — copy and rename for wave-46). Read sibling fences before ANY
   candidate opens.
2. Probes: dispatch ≤5 parallel read-only probe subagents (one per family
   batch), whole-family FRESH, RECEIPTS OVER LISTS — written receipts with
   decline reasons, saved to state/wave46-recon/. No candidates from memory.
   Wave-45 lesson: probe receipts MUST NOT quote machine-local absolute
   paths (publish-public.sh tripwire — sanitize to portable form at write
   time; wave-37 kit violation class).
3. Write state/wave46-leaf-plan.md (candidates, receipts cited, family
   spread, plan size 12-16). Commit recon + leaf plan (explicit paths).
4. Spec phase: batches ≤4 concurrent spec-engineer subagents, compact
   write-NOW prompts, anchor script FIRST with REAL anchor outputs, ONE
   format exemplar. Wave-44/45 lessons: if a spec-engineer goes SILENT ~14
   min past the steer window → stop it and write the spec yourself with
   REAL anchors; commit specs INCREMENTALLY per batch (crash-safety); spec
   prose MUST match the anchor math (anchor is the source of truth — vmcl
   spec-consistency fix cd6dc26c class); all specs em-dash-free, desc ≤
   limits, standards ids in standards-map.
5. Build rounds: 3-4 concurrent builders (ONE subagent per leaf per
   PARALLEL-AGENT doctrine), leaf-create-gate BEFORE every commit (six
   artifacts: SKILL.md + logic + contract test + eval fragment + hit1 yaml
   + ledger row), rate-at-creation ≥9.5 in-turn ledger rows 626+. Tests
   pass under BOTH interpreters; no exact-float equality asserts (wave-42
   class — use order-safe tolerant asserts); contract tests MUST NOT use
   machine-local sys.path (portable import — wave-45 walker-forman
   tripwire); __pycache__ purge before gates; desc ≤ 1000 chars/148 words
   at draft time.
6. Close-out chain (in order): pre-merge sim (zero thefts — wave-45 caught
   3 routing issues pre-merge: vs2 stall-speed 13.5/13.5 tie + fir-bandpass
   hyphenated-token misroutes; reworded fragment queries to carry the new
   leaf's hyphenated name tokens, re-sim before merge) → corpus merge 1266
   + 2N → delete fragments (0 on disk) → family routers (+rows, +guidance
   bullets, parity == leaves, descs ≤1024) → make visuals → **gates FRESH
   at rest**: make validate PASS 5/5 · make attest PASS 3/3 · make
   completeness ALL REQUIRED PASS · make value-delta PASS 10/10 ≥0.2 ·
   make visuals-check PASS · make manifest-check PASS · router descs ≤1024
   · stale-number-guard · em dashes 0 in skills/ · git status clean →
   push PRIVATE (GITHUB_TOKEN_ARJUN only, token-in-URL) → ls-remote verify
   remote main == HEAD → publish-public.sh sanctioned sync (leaf-count
   guard; NO force; NO direct ashfordeOU push — run once; if the
   machine-local path tripwire fires, fix + re-run; do NOT bypass) →
   record ACTUAL public commit (hourly automation may race ahead — verify
   CI attest + release-on-milestone on the ACTUAL public HEAD) → GROUP 160
   close-out post AS OPS MANAGER (your own profile bot) → wave46-state.md
   honest (receipts, disclosures) → commit + push → final report.
7. Final report: concise block in the run log (leaves landed, gates,
   pushes, public HEAD, disclosures, actual spend). Record spend:
   `python3 ~/.hermes/scripts/run_budget.py record --job wave-build-46 --usd <actual>`.

## Budget

wave-build cap $20 (run_budget.py check exit 0 at dispatch: est $18).
Relay cap $5 does not apply to the build itself.

## Hard rules

- **TURN-ALIVE**: never end your turn with a text-only response until the
  final close-out report — a text yield mid-delegation closed the wave-44
  builder session with 9 probe results pending. Use sleep-poll + real tool
  calls between delegations.
- QH gate exit 0 before EVERY batch
  (`python3 ~/.hermes/scripts/quiet-hours-gate.py --check`). Started ~12:30
  UTC — ~7h30m daylight to 20:00 UTC; a full wave ≈3-3.5h, close well
  before the 19:30 UTC guard. If anything slips toward the window, stop
  cleanly and queue the remainder for 08:00 UTC 2026-09-08.
- ONE builder only. No duplicates. No parallel relay dispatch while you run.
- NO direct push to ashfordeOU — publish only via publish-public.sh after
  the private push lands (publish law).
- No founder contact. Routine progress. GROUP 160 post only at close-out.
- Record actuals honestly in wave46-state.md — disclosures over silence
  (wave-30..45 pattern: exact-float flakes, sanitization tripwires, routing
  rewords, spec-engineer stalls, public-sync-raced-ahead all disclosed and
  root-caused).

Relay dispatch 2026-09-07 ~12:30 UTC — same-day dispatch after CEO P5.2
WAVE-45 gate PASSED 9.66/10 (~12:25 UTC). 14/14 leaves landed wave-45
(611→625, corpus 1266, mandate ≥10 MET +4).
