---
name: e2008-protection-diode-life-test
description: "Use when a long duration protection diode endurance run is planned or audited. Evaluate an extended protection diode life test run at worst case conditions under ECSS-E-ST-20-08C clause 9.6.18: derive the junction temperature the forward bias and thermal resistance produce, confirm the stress current and case sit at or above what the mission imposes and below the qualified ceiling, take the Arrhenius acceleration the stress junction holds over the mission junction, convert the run into equivalent mission hours, and hold the forward voltage and reverse leakage drift, the drift rate per thousand hours and the surviving sample against their limits. Trigger: ecss, e-st-20-08c-clause-9-6-18, protection-diode-life-test, diode-junction-temperature-rise, diode-arrhenius-acceleration-factor, diode-equivalent-mission-hours, diode-endurance-parameter-drift, protection-diode-endurance-sample."
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
  tags: [ecss, e-st-20-08-solar-cell-scope, e2008-protection-diode-life-test, protection-diode-life-test, diode-junction-temperature-rise, diode-arrhenius-acceleration-factor, diode-equivalent-mission-hours, diode-endurance-parameter-drift, protection-diode-endurance-sample]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cells -- Protection Diode Life Test (space-systems/ecss/e2008-protection-diode-life-test)

Use when the task is clause 9.6.18 of ECSS-E-ST-20-08C -- the long run
at worst case conditions that stands in for a protection diode's whole
life on an array. The part is fitted once and asked to conduct on the
day something goes wrong, years later. Nothing in a short acceptance
sequence says it still will, so the endurance run is the substitute and
its conditions are the whole of its credibility.

## Domain quick reference

- The junction ages, not the oven. Forward bias puts power into the die,
  the thermal resistance turns that power into a rise, and the junction
  is the case plus that rise. It is derived on every case, never read
  off the chamber setpoint.
- Worst case is a comparison, not an adjective. The stress current and
  the stress case temperature are held against what the mission actually
  imposes, and a run easier than the mission has proved the easier life.
- The ceiling is the other half of that comparison. Pushed above the
  qualified junction maximum the part ages by a mechanism the mission
  never imposes, and the run then describes that mechanism rather than
  the mission's. Hotter is not automatically more conservative.
- Acceleration is an Arrhenius factor between the stress junction and
  the mission junction. It converts test hours into mission hours, and
  it collapses to exactly one when the two junctions are equal: a run
  with no thermal margin buys no mission time at all, however long it is.
- The activation energy is a claim, not a measurement. A low one makes
  the arithmetic honest and a high one makes it flattering, so it
  carries a floor and the acceleration is only derived once the stress
  has been shown representative.
- Stability is measured as drift from where each parameter started:
  forward voltage and reverse leakage, both as fractions. A part that
  ends outside its limits did not survive, whatever the run length says.
- Drift also has a rate. The same fractional move over five hundred
  hours and over five thousand are different findings: the first part is
  still moving, and it has not stabilised, it is simply early.
- A sample is counted by what finished. Devices lost during the run are
  failures in their own right and they do not also count towards the
  surviving population.

## Workflow

1. Validate the endurance policy first: sample floor, allowed failures,
   run length and equivalent mission hour floors, activation energy
   floor, junction margin floor and ceiling, and the three drift limits.
   An equivalent mission floor at or below the run length is refused,
   because it would let an unaccelerated run pass.
2. Derive the stress junction and the mission junction from their case
   temperatures, the forward bias and the thermal resistance, and take
   the margin between them.
3. Check the stress is representative before deriving anything from it:
   junction under the ceiling, margin above its floor, stress current
   and case at or above the mission's, activation energy above its
   floor. If it is not, report the run as stress deficient and derive no
   acceleration figure at all rather than publishing a number nobody can
   use.
4. Take the Arrhenius factor and convert the run into equivalent mission
   hours. A margin or a duration landing exactly on a floor passes; the
   comparison tolerance absorbs representation error and the floor does
   not move.
5. Take the forward voltage and leakage drift as fractions of their
   starting values and the forward drift as a rate per thousand hours,
   and count the devices that finished. Report every finding, not the
   first.
6. Close on one verdict, the stress conditions outranking the rest
   because they decide whether the run described this mission at all:
   life stress deficient, life drift failure, life sample plan
   deficient, or life stability accepted.

## Pitfalls

- Reading the chamber setpoint as the ageing temperature. A forward
  biased diode heats itself, and on a poor thermal path the junction can
  sit tens of degrees above a case that looks perfectly in tolerance.
- Treating hotter as safer. Above the qualified junction maximum a new
  mechanism opens, and the run then measures a failure route the mission
  does not contain while missing the one it does.
- Running at a bias the mission exceeds. An endurance run at half the
  mission current is a long test of an easy life, and it reports
  stability the flight part was never shown to have.
- Quoting an acceleration factor from a run with no thermal margin. The
  Arrhenius factor is exactly one when the junctions match, so the
  headline mission hours then equal the test hours and the run bought
  nothing it claimed.
- Choosing a flattering activation energy. It sits in an exponent, so a
  tenth of an electronvolt moves the equivalent mission hours by a large
  multiple, and the floor is what keeps the claim honest.
- Reporting an end-of-life measurement without its rate. A part inside
  its drift limit but still climbing steadily has not stabilised, and a
  short run is precisely where that goes unnoticed.
- Counting a device that failed mid-run towards the surviving sample.
  The population that finished is what the statistics were written
  against, and a failure is a finding of its own.
- Comparing a derived acceleration or drift against a limit by bare
  arithmetic. These come out of an exponential and a division, which
  land a few units in the last place either side of a limit on different
  hosts, so the comparison absorbs that error while the limit itself is
  never relaxed.

## Behavior contract (gate 3)

The policy validation, forward dissipation and junction temperature
derivations, the worst case and ceiling comparisons, the Arrhenius
acceleration factor and equivalent mission hours, the forward voltage
and leakage drift fractions, the drift rate per thousand hours, the
surviving device count and the endurance verdict are exercised by the
gate 3 contract test:
scripts/test_e2008_protection_diode_life_test.py against
scripts/e2008_protection_diode_life_test_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2008_protection_diode_life_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
