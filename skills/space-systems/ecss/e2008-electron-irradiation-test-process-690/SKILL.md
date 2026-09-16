---
name: e2008-electron-irradiation-test-process-690
description: "Use when such a run is planned or audited. Verify that a one megaelectronvolt electron irradiation of planar blocking diodes followed the method ECSS-E-ST-20-08C clause 12.6.11.2.2 states: hold the beam energy inside its tolerance, keep every segment inside the rate window, integrate flux over time into cumulative fluence and reconcile each planned point, refuse a ladder that does not rise or changed bias part way, and refuse a run missing a step readout or a control part. Trigger: ecss, e-st-20-08c-clause-12-6-11-2-2, planar-blocking-diode-electron-irradiation-run, one-mev-electron-beam-energy-tolerance, blocking-diode-fluence-step-ladder, irradiation-bias-condition-consistency, blocking-diode-post-step-characterisation, unirradiated-control-part-drift."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-electron-irradiation-test-process-690, planar-blocking-diode-electron-irradiation-run, one-mev-electron-beam-energy-tolerance, blocking-diode-fluence-step-ladder, irradiation-bias-condition-consistency, blocking-diode-post-step-characterisation, unirradiated-control-part-drift]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Planar Blocking Diodes -- One Megaelectronvolt Electron Irradiation Process (space-systems/ecss/e2008-electron-irradiation-test-process-690)

Use when the task is clause 12.6.11.2.2 of ECSS-E-ST-20-08C -- running
or reviewing the exposure itself. Planar blocking diodes are put in
front of a one megaelectronvolt electron beam under a stated method, and
the work here is checking that what was actually delivered is that
method.

## Domain quick reference

- A run is not one exposure. It is a ladder of fluence points, and the
  parts come out and are measured at each one, so the campaign ends with
  a degradation curve rather than a single before-and-after pair.
- The energy names the method. One megaelectronvolt is the reference
  electron the mission environment is folded into, so a beam a long way
  off it is delivering damage that no equivalence was written for.
- The rate matters as well as the total. Too slow and the run never
  finishes; too fast and the injected carrier density starts annealing
  the damage as it is made, so the same fluence leaves less degradation
  than flight would.
- The fluence a step reached is the flux it ran at over the time it ran
  for, summed across every segment. Beam hours are not a level, and a
  step interrupted and restarted has two segments, not one.
- The ladder points are cumulative. A step is judged against the total
  fluence the parts have seen by the end of it, not against its own
  increment, because the degradation curve is drawn against accumulated
  exposure.
- The points have to rise, and a repeated point is not a rise. Two steps
  at the same fluence produce two readings of one condition and no new
  place on the curve.
- The bias condition during exposure changes the damage a given fluence
  does, because the field across the junction sets where the carriers
  are while the displacements are being made. It is declared, it is one
  of the recognised states, and it is held across the ladder or the
  steps are not points on one curve.
- The two parameters move for different reasons. A rising forward drop
  is base transport being lost; a growing reverse leakage is generation
  in the depletion region. One is reported as a difference, the other as
  a ratio, because that is how each of them scales.
- An unirradiated control part is carried through the same readouts. A
  forward drop that walks a few millivolts on the bench looks exactly
  like a small radiation effect, and without a control nothing separates
  them.

## Workflow

1. Validate the policy, then every step: a target fluence point, a
   recognised bias state, at least one exposure segment, and all four
   readouts either side of the step.
2. Take the beam energy against the nominal electron and hold the error
   inside the stated tolerance, with a value exactly on the tolerance
   admitted.
3. Check every exposure segment's flux against the rate window, and
   report how many fell outside it and where the first one was, not just
   that one did.
4. Integrate flux over duration into a per-step fluence and run those up
   into cumulative points.
5. Reconcile each cumulative point with its planned target as a signed
   fraction, so a shortfall and an overshoot are distinguishable rather
   than both reading as an error.
6. Refuse a ladder whose points do not genuinely rise, and refuse one
   whose bias state changed part way, naming every state it was run
   under.
7. Take the forward drop rise as a difference and the reverse leakage
   growth as a ratio, across the whole ladder.
8. Take the control part's drift and hold it under its allowance, then
   close on one verdict -- not performed, beam outside the method,
   ladder invalid, characterisation incomplete, or accepted -- with
   every finding listed, not only the one that set the verdict.

## Pitfalls

- Reporting beam hours as the test level. Hours are not a fluence
  without the flux they ran at, and the flux is the number that drifts.
- Judging a step against its own increment. The parts carry everything
  delivered before it too, and the curve is drawn against the
  accumulated total.
- Letting a step be repeated to fill a schedule gap. It adds a reading
  and no point, and it inflates the apparent size of the campaign.
- Changing the bias state between steps because the fixture was easier
  that way. The steps then describe two different damage conditions and
  no single curve passes through them.
- Running the beam hot to save days. Excess injected carrier density
  anneals displacement damage while it is being created, and the part
  comes out looking harder than flight will find it.
- Reporting leakage growth as a difference. It moves over decades, and a
  difference in microamperes hides whether it doubled or went up a
  hundredfold.
- Skipping the readout before a step because the one after the previous
  step is the same measurement. It is the same only if nothing moved in
  between, which is precisely what the readout exists to establish.
- Running without a control part. Bench drift of a few millivolts is
  indistinguishable from an early radiation effect, and the first step
  of the ladder is exactly where that matters.

## Behavior contract (gate 3)

The policy validation, per-step validation of target, bias state,
segments and all four readouts, beam energy error and its
tolerance-inclusive band, the flux rate window with its inclusive
ceiling, segment and step fluence integration, cumulative points, signed
reconciliation against each planned point, the strict-rise ladder check,
bias-state consistency, forward drop rise as a difference, leakage
growth as a ratio, control-part drift and every verdict branch are
exercised by the gate 3 contract test:
scripts/test_e2008_electron_irradiation_test_process_690.py against
scripts/e2008_electron_irradiation_test_process_690_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_electron_irradiation_test_process_690.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
