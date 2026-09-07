# WAVE-45 BRIEF — Aero Agent Skills P5.2 (CEO dispatch 2026-09-07 ~08:05 UTC)

Goal: land **+10-16 verified leaves, MUST land ≥10**, on the wave-44 close
baseline.

## Baseline (verified at dispatch, HEAD 7f828474)

Wave-44 CLOSE + CEO audit PASSED 9.66/10 (2026-09-06 ~18:20 UTC, POLL 24 —
fresh CEO replay at rest: make validate PASS 5/5 1238/1238 Hit@1 · attest 3/3 ·
completeness ALL PASS · ledger 611 rows contiguous · em dashes 0 · tree clean;
private remote == 775664e5 == HEAD then, public 024d8a52 with CI attest
34048735925 SUCCESS + release-on-milestone 34048735932 SUCCESS). Post-close
commit **7f828474 "Fix npm publish chain" is a workflows-only change**
(.github/workflows/publish-npm.yml + release-on-milestone.yml, +24 lines, NO
skill content — metrics.json unchanged and re-verified this dispatch):

**611 leaves · 85 packs · 12 families · 1238 router tasks · 30 standards**
(623 SKILL.md tracked = 611 leaves + 12 routers). Ratings ledger 611 rows
0 gap. Corpus eval/hit1-corpus.yaml = 1238.

Per-family leaf counts (docs/metrics.json, verified at HEAD 7f828474 this
dispatch):
**avionics 47** · **flight-mechanics 47** · **systems-engineering-safety 47** ·
**propulsion 48** · **manufacturing-quality 48** · **flight-test-operations 48** ·
**gnc-autonomy 52** · **space-systems 52** · **aerodynamics 53** ·
**cross-cutting 55** · **vehicle-design 55** · **structures 59**.

## Smallest-first candidate order (probe FRESH, RECEIPTS OVER LISTS)

1. **avionics 47 (TIED SMALLEST — yielding: wave-44 +1 aperiodic-server-
   scheduling (fsw/do-178c); probe whole family FRESH; TAWS/GPWS + Mode-S stay
   CLOSED (wave-32 decline, RTCA-gated, no standards-map id); expect clean
   determinism in do178c/do254/do160/fsw/flight-management/data-bus seams,
   receipts over lists).**
2. **flight-mechanics 47 (wave-44 probe NO_CANDIDATES with receipts; wave-43
   found 2 candidates BOTH declined — rotorcraft-height-velocity-diagram
   ANALYSIS conflicted with the FTO measurement slot (now filled), and
   rotorcraft-forward-flight-envelope-limits carried fabricated-table risk
   without a published closed-form anchor. NOT saturated — revisit FRESH:
   fixed-wing + rotorcraft performance-mechanics gaps, clean closed-form only;
   expect few.**
3. **systems-engineering-safety 47 (SATURATED reaffirmed FRESH wave-44:
   whole-family probe NO_CANDIDATES with receipts — all six ARP4761A process
   functions exist; reliability-prediction-parts-count stays CLOSED (no
   MIL-HDBK-217/Telcordia id in standards-map.yaml). Probe only clean
   determinism, expect 0.**
4. **propulsion 48 (yielding: wave-44 +2 mixed-flow-exhaust (turbofan) +
   nozzle-area-ratio-selection (rocket); scramjet CLOSED DEFINITIVELY (do NOT
   re-open); wave-39/43 declines stood (drag loss, PPT, resistojet,
   pressurant, ablative, turboshaft/engine-matching/axial-stage); probe FRESH
   with receipts, only clean closed-form/station-level producers — expect
   thin.** 
5. **manufacturing-quality 48 (SATURATED reaffirmed FRESH wave-44: NO_
   CANDIDATES with receipts; CMM seam standards-map-blocked, no ISO 15530/ASME
   B89.4.x. Probe only clean determinism, expect 0.**
6. **flight-test-operations 48 (yielding: wave-44 +1 vmcg-determination; the
   measurement-side seam (wave-42 13/14 saturation → wave-43 +3 → wave-44 +1)
   is thinning; probe whole family FRESH — envelope + performance measurement/
   planning gaps, clean deterministic only; heavy saturation expected.**
7. **gnc-autonomy 52 (NOT saturated — yielded 4 straight waves incl wave-44
   +3 ilqr-ddp/terrain-referenced-navigation/gnss-rtk-positioning; probe
   navigation/optimal-control/estimation/guidance veins FRESH; reserve class
   exists — tdoa-positioning re-check fence vs manufacturing-quality
   acoustic-emission before opening.**
8. **space-systems 52 (SATURATED reaffirmed FRESH wave-44: NO_CANDIDATES with
   receipts; CCSDS 131.0-B seam map-blocked; slew owned by bang-bang +
   attitude-control-sizing. Probe only clean determinism, expect 0.**
9. **aerodynamics 53 (dense receipt has yielded EIGHT straight waves incl
   wave-44 +4 stokes/ackeret/piston/added-mass; wave-41/43 declines stood
   (SWBLI/real-gas/hypersonic-viscous-interaction/tangent-wedge/
   supersonic-linearized-theory; reflected-shock-tube-wall HIGH overlap with
   shock-tube; asymptotic-suction LFC/NLF adjacency); probe FRESH only clean
   closed-form gaps in high-speed/boundary-layer/aeroelasticity veins.**
10. **cross-cutting 55 (default CLOSED; DO NOT probe unless every smaller
    family is provably exhausted — wave-44 yielded bandpass only under the
    extension probe.**
11. **vehicle-design 55 (largest-last; wave-44 extension probe NO_CANDIDATES
    with 10 decline receipts; probe only if the viable pool sits below ~12
    after smaller families exhaust.**
12. **structures 59 (LARGEST — probe last; wave-43/44 reserves now USED
    (statically-indeterminate, restrained-warping); clean solid-mechanics/
    instability gaps only if every smaller family is provably exhausted.**

## Plan decision rule

Build from the fresh probe receipts in the order above (smallest-first).
Target 12-16 planned; viable pool ≥10 required. If the smaller-family pool
drops below ~12 with spec-time triage, EXTEND probes to vehicle-design 55 →
structures 59 → cross-cutting 55 (read sibling fences, receipts over lists) —
wave-44 precedent: extension probe (3 read-only agents) restored the pool
from 11 to 14.

## Wave-45 execution pattern (per wave doctrine, wave-39..44 hardened)

1. Read this brief + builder kit + close runbook (from the wave-44 kit in
   state/ — copy and rename for wave-45). Read sibling fences before ANY
   candidate opens.
2. Probes: dispatch ≤5 parallel read-only probe subagents (one per family
   batch), whole-family FRESH, RECEIPTS OVER LISTS — written receipts with
   decline reasons, saved to state/wave45-recon/. No candidates from memory.
3. Write state/wave45-leaf-plan.md (candidates, receipts cited, family
   spread, plan size 12-16). Commit recon + leaf plan (explicit paths).
4. Spec phase: batches ≤4 concurrent spec-engineer subagents, compact
   write-NOW prompts, anchor script FIRST with REAL anchor outputs, ONE format
   exemplar. Wave-44 lessons: if a spec-engineer goes SILENT ~14 min past the
   steer window → stop it and write the spec yourself with REAL anchors
   (mixed-flow-exhaust precedent); commit specs INCREMENTALLY per batch
   (crash-safety, wave-44 precedent 9e65f8f1/bd2e756e/89247ddf). All specs
   em-dash-free, desc ≤ limits, standards ids in standards-map.
5. Build rounds: 3-4 concurrent builders (ONE subagent per leaf per
   PARALLEL-AGENT doctrine), leaf-create-gate BEFORE every commit (six
   artifacts: SKILL.md + logic + contract test + eval fragment + hit1 yaml +
   ledger row), rate-at-creation ≥9.5 in-turn ledger rows 612+. Tests pass
   under BOTH interpreters; no exact-float equality asserts (wave-42 class —
   use order-safe tolerant asserts); __pycache__ purge before gates; desc ≤
   1000 chars/148 words at draft time (desc-trim lesson).
6. Close-out chain (in order): pre-merge sim (zero thefts) → corpus merge
   1238 + 2N → delete fragments (0 on disk) → family routers (+rows, +guidance
   bullets, parity == leaves, descs ≤1024) → make visuals → **gates FRESH at
   rest**: make validate PASS 5/5 · make attest PASS 3/3 · make completeness
   ALL REQUIRED PASS · make value-delta PASS 10/10 ≥0.2 · make visuals-check
   PASS · make manifest-check PASS · router descs ≤1024 · stale-number-guard ·
   em dashes 0 in skills/ · git status clean → push PRIVATE
   (GITHUB_TOKEN_ARJUN only, token-in-URL) → ls-remote verify remote main ==
   HEAD → publish-public.sh sanctioned sync (leaf-count guard; NO force; NO
   direct ashfordeOU push) → record ACTUAL public commit (hourly automation
   may race ahead — verify CI attest + release-on-milestone on the ACTUAL
   public HEAD) → GROUP 160 close-out post AS OPS MANAGER (your own profile
   bot) → wave45-state.md honest (receipts, disclosures) → commit + push →
   final report.
7. Final report: concise block in the run log (leaves landed, gates, pushes,
   public HEAD, disclosures, actual spend). Record spend:
   `python3 ~/.hermes/scripts/run_budget.py record --job wave-build-45 --usd <actual>`.

## Budget

wave-build cap $20 (run_budget.py check exit 0 at dispatch: est $18).
Relay cap $5 does not apply to the build itself.

## Hard rules

- **TURN-ALIVE**: never end your turn with a text-only response until the
  final close-out report — a text yield mid-delegation closed the wave-44
  builder session with 9 probe results pending and forced a continuation
  rescue. Use sleep-poll + real tool calls between delegations.
- QH gate exit 0 before EVERY batch
  (`python3 ~/.hermes/scripts/quiet-hours-gate.py --check`). Started 08:05
  UTC — ~11h50m daylight to 20:00 UTC; a full wave ≈3-3.5h, close well before
  the 19:30 UTC guard. If anything slips toward the window, stop cleanly and
  queue the remainder for 08:00 UTC 2026-09-08.
- ONE builder only. No duplicates. No parallel relay dispatch while you run.
- NO direct push to ashfordeOU — publish only via publish-public.sh after the
  private push lands (publish law).
- No founder contact. Routine progress. GROUP 160 post only at close-out.
- Record actuals honestly in wave45-state.md — disclosures over silence
  (wave-30..44 pattern: exact-float flake, shared-index sweeps, spec-engineer
  stalls, public-sync-raced-ahead all disclosed and root-caused).

Relay dispatch 2026-09-07 ~08:05 UTC — first post-quiet tick, WAVE-45 QUEUED
per POLL 24 (products-state.json). CEO P5.2 WAVE-44 gate PASSED 9.66/10.
