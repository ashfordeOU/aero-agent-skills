---
name: q6013-magnetics-procurement-test-table
description: "Evaluate a commercial magnetic part lot against its procurement test matrix under ECSS-Q-ST-60-13C Table 8-5: validate each row's method, sample size and accept number, correct every winding-resistance reading back to the reference temperature before it meets its limit, apply a maximum to resistance, a minimum to insulation resistance and a two-sided band to inductance and turns ratio instead of one comparison for all rows, refuse a dielectric run carried out below the declared test voltage, and weigh row failures as a percent defective against the allowance. Use when inductor or transformer procurement test data has to become a lot verdict. Trigger: ecss, q-st-60-13c-table-8-5, magnetics-procurement-test-matrix, winding-resistance-temperature-correction, magnetics-insulation-resistance-minimum, turns-ratio-tolerance-band, dielectric-withstanding-leakage-limit, magnetics-lot-accept-number."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-magnetics-procurement-test-table, q-st-60-13c-table-8-5, magnetics-procurement-test-matrix, winding-resistance-temperature-correction, magnetics-insulation-resistance-minimum, turns-ratio-tolerance-band, dielectric-withstanding-leakage-limit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial Parts — Magnetics Procurement Test Table (space-systems/ecss/q6013-magnetics-procurement-test-table)

Use when the task is the magnetic-parts row of the procurement testing
provisions of ECSS-Q-ST-60-13C Table 8-5 — taking the test methods, sample
sizes and acceptance limits the table sets for inductors and transformers and
turning an executed campaign on one purchased lot into an accept-or-hold
verdict.

## Domain quick reference

- A winding resistance is a thermometer as much as a measurement. Copper
  moves about 0,4 % per degree, so a part measured on a warm bench reads
  several percent high and fails a limit it would have met. The reading is
  corrected to the reference temperature the limit is quoted at before any
  comparison, and a reading delivered without its temperature is not a
  result.
- The correction is a ratio about the inferred zero-resistance temperature of
  the conductor, not a percentage added on. Using a linear percentage away
  from room temperature drifts fast at cryogenic and hot-bench extremes,
  which is exactly where an acceptance argument is contested.
- The limits on this table take three different shapes. Winding resistance
  carries a maximum, insulation resistance carries a minimum, and inductance
  and turns ratio carry two-sided bands. One comparison applied to all of
  them passes every open winding on the insulation row.
- A dielectric-withstanding run is graded on leakage at a declared voltage,
  and a run carried out below that voltage is not a weaker pass. The stress
  was never applied, so the sample has no result and the run is refused
  rather than graded.
- Turns ratio and inductance are band quantities because a magnetics fault
  moves them either way: a shorted turn drops both, a mis-set gap or a wrong
  core lifts inductance. Recording only an upper bound loses the shorted-turn
  population entirely.

## Workflow

1. Validate each matrix row: a sample larger than the lot, a zero sample, an
   accept number above the sample or more failures than units sampled is an
   input error, not a degenerate case to clamp. Refuse a matrix that repeats
   a method, so every row is judged once.
2. Correct every winding-resistance reading from its measurement temperature
   to the reference temperature, refusing a temperature at or below the
   inferred zero where the ratio is undefined.
3. Judge each measured quantity against the shape of its own limit — maximum,
   minimum or band — and report the under-bound and over-bound populations
   separately rather than as one failure count.
4. Grade the dielectric-withstanding leakage against its limit, refusing a run
   whose applied voltage fell short of the declared test voltage.
5. Absorb floating-point representation error at every bound with a named
   tolerance rather than by relaxing the bound.
6. Convert each row's failures into a percent defective, compare it with the
   allowance as well as the accept number, and report every rejecting row
   with a marginal-row advisory where an accepted row used up its allowance.

## Pitfalls

- Comparing a hot winding resistance straight to the limit. The part is
  rejected for the bench it sat on, and a supplier who measures cold ships
  the same build through.
- Applying a maximum to insulation resistance. The comparison passes a
  winding whose insulation has broken down to a few ohms, which is the one
  result the row exists to find.
- Reading turns ratio against an upper bound only. A shorted turn shows as a
  low ratio and walks through a one-sided check.
- Grading a dielectric run performed under the declared voltage. It is not a
  softer pass; no stress was applied, so there is nothing to grade.
- Widening a bound to pass an exact-equality case. An equality at the bound is
  a representation question handled by the tolerance inside the comparison;
  the declared bound stays as specified.

## Behavior contract (gate 3)

The row validation, winding-resistance temperature correction, the maximum,
minimum and band limit shapes, the dielectric-withstanding run and the overall
accept-or-hold disposition are exercised by the gate 3 contract test:
scripts/test_q6013_magnetics_procurement_test_table.py against
scripts/q6013_magnetics_procurement_test_table_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_magnetics_procurement_test_table.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
