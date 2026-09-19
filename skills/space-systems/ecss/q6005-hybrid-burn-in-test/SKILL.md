---
name: q6005-hybrid-burn-in-test
description: "Evaluate a hybrid burn-in exposure and the lot it was run on, under ECSS-Q-ST-60-05C clause 10.3.9. Use when the task is proving a schedule is an Arrhenius equivalent of the reference condition rather than merely hotter, refusing a stress temperature that accelerates nothing, taking the die temperature the bias produces through the package rather than the oven setting, grading a surviving unit on how far it drifted and how promptly it was read, and deciding whether the reject fraction condemns the population. Trigger: ecss, q-st-60-05c, hybrid-burn-in-schedule, arrhenius-burn-in-equivalence, hybrid-burn-in-junction-temperature-limit, hybrid-burn-in-delta-drift-limit, hybrid-burn-in-measurement-window, hybrid-burn-in-lot-percent-defective."
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
  tags: [ecss, q-st-60-05-hybrid-scope, q6005-hybrid-burn-in-test, hybrid-burn-in-schedule, arrhenius-burn-in-equivalence, hybrid-burn-in-junction-temperature-limit, hybrid-burn-in-delta-drift-limit, hybrid-burn-in-lot-percent-defective]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrid Screening — Hybrid Burn-in Test (space-systems/ecss/q6005-hybrid-burn-in-test)

Use when the task is the burn-in of ECSS-Q-ST-60-05C clause 10.3.9 —
running the hybrid hot and biased for long enough that the weak members
of the batch fail on the bench, and judging whether the schedule that
was run actually did that.

## Domain quick reference

- Burn-in is a powered exposure. The mechanism it precipitates needs
  current as well as heat, so an unpowered oven soak of the same length
  and temperature is a bake with the burn-in name on the traveller.
- Temperature buys time at a rate set by the activation energy of the
  mechanism. A shorter run at a higher temperature is admissible when
  it is an Arrhenius equivalent of the stated reference condition, and
  the equivalence is computed, not asserted. A low-energy mechanism is
  accelerated far less by the same temperature step than a high-energy
  one, so the equivalence depends on what the screen is aimed at.
- A stress temperature that is not above the use temperature
  accelerates nothing. The arithmetic still returns a number in that
  case, and the number at or below unity is the finding rather than
  the result.
- The temperature that matters is on the die. Bias dissipates power,
  the power raises the junction above ambient through the thermal
  resistance of the package, and a schedule that reads safely as an
  oven setting can sit above the maximum rating where the circuit is.
- A surviving unit is graded on how far it moved, not only on where it
  ended. A device still inside its specification limits but well
  outside its allowed drift has reported something about the batch,
  and the reading has to be taken inside the window before recovery
  quietly removes the evidence.
- The lot is graded as well as the units. Burn-in exists to expose a
  weak population; a reject fraction above the allowable for the flow
  class says the population is the problem, and the survivors are not
  made sound by having survived.

## Workflow

1. Validate each record: identifier, mechanism, flow class, use and
   ambient temperature, duration, dissipated power, thermal
   resistance, bias flag, measurement delay, the pre and post readings
   and the approval flag. An unknown mechanism or flow class, a
   temperature at or below absolute zero and a non-positive duration
   are input errors.
2. Compute the acceleration factor between the use and stress
   temperatures for this mechanism, and raise a finding when it does
   not exceed unity.
3. Compute the duration this stress temperature owes to match the
   reference condition, and compare the exposure that was run.
4. Separate the two ways a short run can be wrong: shorter than its
   own equivalent duration is a shortfall; equal to it but shorter
   than the reference run is a reduced-duration equivalence, and that
   needs an approval on record.
5. Take the junction temperature from ambient, power and thermal
   resistance, and grade it against the maximum rating.
6. Grade the outcome: bias applied, the reading taken inside the
   window, the drift inside its limit, and any failure during the
   exposure, each as its own finding.
7. Aggregate the lot for the stated flow class: surviving and failed
   units, the reject fraction, the allowable it is graded against, and
   the lot disposition.

## Pitfalls

- Running the oven without the bias. Everything downstream looks the
  same on paper and the mechanism the screen exists for was never
  driven.
- Shortening the run because the oven was hotter, without computing
  the equivalence for the mechanism in question. The same temperature
  step is worth very different numbers of hours at different
  activation energies.
- Reading the oven setting as the stress temperature. On a dissipating
  hybrid the die sits well above ambient, and the schedule that looked
  conservative can be over the maximum junction rating.
- Accepting a unit because it still meets its limits. The drift across
  the exposure is the signal; a part that moved most of its band in
  one hundred and sixty hours is not the part it was before.
- Measuring the survivors next week. Drift recovers, and a late
  reading turns the evidence the screen produced into a clean sheet.
- Shipping the survivors of a lot that failed its percent-defective
  allowable. The reject fraction is a statement about the population,
  and the units that happened not to fail belong to the same one.

## Behavior contract (gate 3)

The Arrhenius acceleration factor, reference equivalence and required
duration, junction temperature, drift fraction, bias and measurement
window checks, the reduced-duration approval rule and the flow-class
lot grading are exercised by the gate 3 contract test:
scripts/test_q6005_hybrid_burn_in_test.py against
scripts/q6005_hybrid_burn_in_test_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q6005_hybrid_burn_in_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
