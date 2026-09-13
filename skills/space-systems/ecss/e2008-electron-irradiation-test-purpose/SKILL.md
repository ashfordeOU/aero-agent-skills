---
name: e2008-electron-irradiation-test-purpose
description: "Evaluate whether a planned electron irradiation run can do what ECSS-E-ST-20-08C clause 6.4.3.11.1 asks of it: stand in for a whole mission's trapped-electron exposure and show how much of a solar cell's electrical performance that exposure takes away. Use when such an accelerated-life campaign is scoped or its plan is reviewed: turn annual equivalent fluence, mission duration and margin into the end-of-life fluence, check the planned fluence steps rise, carry enough cells and reach that fluence, bound the beam acceleration from both sides, predict current, voltage and maximum-power retention from the logarithmic fit, and compare with the power budget. Trigger: ecss, e-st-20-08c, clause-6-4-3-11-1, solar-cell-electron-irradiation-purpose, electron-equivalent-fluence-accumulation, irradiation-acceleration-factor-bound, solar-cell-degradation-fit, end-of-life-power-retention."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e-st-20-08c, e2008-electron-irradiation-test-purpose, solar-cell-electron-irradiation-purpose, electron-equivalent-fluence-accumulation, irradiation-acceleration-factor-bound, solar-cell-degradation-fit, end-of-life-power-retention]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies — Electron Irradiation Test Purpose (space-systems/ecss/e2008-electron-irradiation-test-purpose)

Use when the task is the purpose rule of ECSS-E-ST-20-08C clause 6.4.3.11.1 —
showing that an electron irradiation run on solar cells is a credible
accelerated stand-in for the mission, so the performance loss it measures is
the loss the array will actually suffer rather than an artefact of the beam
that produced it.

## Domain quick reference

- The damage is displacement damage. Energetic electrons knock atoms out of the
  semiconductor lattice; the defects left behind shorten minority-carrier
  lifetime, and the cell loses current first, power next and voltage least.
  That ordering is a sanity check on any measured result.
- A whole spectrum is reduced to one number before the test is planned. The
  trapped and solar electron environment is folded into an equivalent fluence
  at a single reference energy, so the run has one knob to turn. Everything
  downstream is that fluence times the mission years times the design margin.
- Retention follows a logarithm, not a line. A parameter's surviving fraction
  falls roughly as one minus a coefficient times the logarithm of one plus the
  fluence over a reference fluence, which is why the first decade of exposure
  costs far more than the last and why a single end-point measurement cannot be
  interpolated backwards.
- Acceleration is bounded on both sides. Below unity the beam is slower than
  the environment and the run is not a life test at all; far above the bound the
  beam deposits damage faster than the cell's own recovery processes remove it,
  and the measured loss exceeds anything flight would produce.
- A fluence step needs a population. One cell at a level cannot separate a
  degradation trend from a single weak part, and three levels are the fewest
  that show a curve rather than a straight line drawn through two points.

## Workflow

1. Derive the end-of-life equivalent fluence from the annual figure, the
   mission duration and the design margin. Reject a margin below unity: an
   unmargined environment is not a qualification target.
2. Validate the planned fluence steps as a strictly rising sequence, since a
   repeated or falling level makes the degradation curve unreadable.
3. Check the step count against the minimum a trend needs and each level's cell
   count against the minimum a level needs, reporting each shortfall in its own
   right.
4. Check the highest planned level reaches the end-of-life fluence, treating a
   level sitting exactly on it as adequate — the tolerance belongs on the
   comparison, never on the target.
5. Form the mission mean flux from the annual fluence and the acceleration
   factor from the beam flux against it, then bound the factor below at unity
   and above at the declared ceiling.
6. Apply the logarithmic fit at the end-of-life fluence to every declared
   parameter and compare the maximum-power retention with the fraction the
   power budget assumes.
7. Report the derived fluence, acceleration, total beam time, per-parameter
   retention, every finding and the verdict.

## Pitfalls

- Planning the run against the annual environment. The test has to reach what
  the mission accumulates, so annual fluence times years times margin is the
  target, and a run sized on the yearly figure under-tests by the mission
  duration itself.
- Taking a single end-point exposure. With a logarithmic law, one before-and-
  after pair fixes no curve, so nothing can be said about performance at any
  intermediate time in the mission.
- Turning the beam up to shorten the campaign. Past the acceleration bound the
  damage arrives faster than the cell's recovery removes it, and the run then
  reports a loss the array will never see, which is as costly a wrong answer as
  an optimistic one.
- Reading the current loss as the power loss. The three parameters degrade at
  different rates, so the maximum-power coefficient is the one the power budget
  needs, and substituting the short-circuit current figure understates the loss.
- Running one cell per fluence level. A degradation point with no population
  behind it cannot be separated from a weak individual part, and the curve then
  rests on whichever cell happened to be worst.
- Comparing retention with a budget that already includes the same margin. The
  margin belongs either on the fluence or on the required fraction; applied
  twice it quietly doubles the qualification.

## Behavior contract (gate 3)

The end-of-life fluence derivation, fluence-step validation and coverage checks,
mission mean flux, two-sided acceleration bound, logarithmic retention fit and
the end-of-life power comparison are exercised by the gate 3 contract test:
scripts/test_e2008_electron_irradiation_test_purpose.py against
scripts/e2008_electron_irradiation_test_purpose_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_electron_irradiation_test_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
