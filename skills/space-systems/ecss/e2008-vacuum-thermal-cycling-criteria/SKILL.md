---
name: e2008-vacuum-thermal-cycling-criteria
description: "Use when accepting or rejecting a vacuum-cycled coupon. Evaluate how far a photovoltaic coupon may degrade after vacuum thermal cycling under ECSS-E-ST-20-08C clause 5.5.3.11.3: report the pre-cycling and post-cycling illuminated readings back to reference irradiance and cell temperature, form the loss fraction of maximum power, short-circuit current and open-circuit voltage against their own allowances, then judge the post-cycling insulation resistance against its floor, against the decades it lost relative to the pre-cycling value and against the leakage current it implies at the declared test voltage. Trigger: ecss, e-st-20-08c, clause-5-5-3-11-3, vacuum-cycling-acceptance-criteria, coupon-performance-degradation, post-cycling-insulation-resistance, insulation-decade-loss, coupon-leakage-current, dielectric-breakdown-after-cycling."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-vacuum-thermal-cycling-criteria, vacuum-cycling-acceptance-criteria, coupon-performance-degradation, post-cycling-insulation-resistance, insulation-decade-loss, coupon-leakage-current]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies — Vacuum Cycling Acceptance Criteria (space-systems/ecss/e2008-vacuum-thermal-cycling-criteria)

Use when the task is the clause 5.5.3.11.3 acceptance decision of
ECSS-E-ST-20-08C: a photovoltaic coupon has come out of its vacuum thermal
cycling run, and it is admissible only if the performance it still delivers
and the insulation resistance it still holds sit inside the degradation the
specification allows.

## Domain quick reference

- The verdict rests on two independent conditions, and both are pre-versus-post
  comparisons of the same coupon. Performance: the illuminated output after
  the run retains the required fraction of what it delivered before. Insulation:
  the resistance between the active circuit and the structure is still high
  enough, and has not collapsed relative to where it started.
- One power number hides which mechanism moved. Maximum power, short-circuit
  current and open-circuit voltage degrade for different reasons — current
  follows optical and cell-area losses, voltage follows junction and shunt
  damage, power follows both plus series resistance — so each carries its own
  allowance and each is reported.
- Raw readings are not comparable. Power and current scale with irradiance and
  both move with cell temperature, so the two measurement sessions are reported
  back to reference irradiance and reference cell temperature before any loss
  fraction is formed. Open-circuit voltage is corrected for temperature only,
  which is why a comparison formed across two very different irradiances is
  flagged rather than trusted.
- Insulation resistance is judged three ways because one way is not enough. A
  floor catches a coupon that would leak into the structure in flight; the
  decades lost catch a coupon that is still nominally above the floor after
  falling two orders of magnitude, which is a mechanism running, not noise; the
  leakage current turns the resistance into the quantity the power system
  actually sees at the declared test voltage.
- A dielectric breakdown is not a large decade loss. There is no meaningful
  resistance to report, so it is carried as its own outcome rather than folded
  into a ratio that would pollute any aggregation.
- A degradation that comes back negative is an improvement, and it is
  admissible — the conditions are one-sided — but it is reported as what it is,
  because a large apparent gain usually points at a measurement or correction
  error worth chasing.

## Workflow

1. Correct the pre-cycling and the post-cycling readings of all three
   illuminated parameters to reference irradiance and reference cell
   temperature, using the coupon's own coefficients where it carries them.
   Refuse a correction whose temperature factor is not positive rather than
   returning a sign-inverted value.
2. Form the loss fraction and the retention ratio of each parameter and compare
   each with its own allowance. A loss landing exactly on an allowance
   complies; the comparison tolerance absorbs representation error and the
   allowance does not move.
3. Check the irradiance difference between the two sessions before trusting the
   open-circuit voltage comparison, and report it when it is too wide for a
   temperature-only correction.
4. Judge the insulation: a declared breakdown ends the assessment with its own
   outcome; otherwise compare the post-cycling resistance with its floor, with
   the decades it lost relative to the pre-cycling value, and with the leakage
   the test voltage drives through it.
5. Aggregate the performance and insulation findings into one list. The coupon
   is accepted only when that list is empty, and every finding names the
   measured value and the value it owed.

## Pitfalls

- Comparing raw watts or raw amperes across the run. An irradiance or cell
  temperature difference between the two sessions can manufacture a loss on an
  undamaged coupon, or mask a real one.
- Grading maximum power alone. A coupon that lost current and gained fill
  factor can show an innocuous power figure while the mechanism that ate the
  current is still running.
- Correcting open-circuit voltage for irradiance as if it scaled. It does not
  scale the way current does, so the honest move is to compare it only across
  sessions at similar irradiance and to say so when they are not.
- Accepting an insulation resistance because it cleared the floor. A coupon
  that fell from ten gigaohms to two hundred megaohms cleared the floor and
  still lost most of its margin; the decade comparison is what sees that.
- Recording a breakdown as an enormous decade loss. An unbounded ratio
  pollutes any aggregation; the breakdown is its own outcome and its own
  finding.
- Widening an allowance to let an exactly compliant coupon through. Equality
  at an allowance is a representation question, handled by the tolerance inside
  the comparison.

## Behavior contract (gate 3)

The reference-condition correction, the per-parameter degradation comparison,
the irradiance-comparability guard, the insulation floor, decade-loss and
leakage checks, the breakdown outcome and the aggregated verdict are exercised
by the gate 3 contract test:
scripts/test_e2008_vacuum_thermal_cycling_criteria.py against
scripts/e2008_vacuum_thermal_cycling_criteria_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_vacuum_thermal_cycling_criteria.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
