---
name: e2008-diode-temperature-annealing-test
description: "Use when an annealing stability result for protection diodes is written or audited. Verify that an external protection diode holds its electrical parameters through a high temperature annealing soak under ECSS-E-ST-20-08C clause 9.6.13: hold the soak profile against its floors and against the package rating, turn temperature and time into equivalent hours at the reference temperature through an Arrhenius factor, count the devices the plan actually draws from the annealing subgroup, match the two reading temperatures, and take the forward voltage drift, the reverse leakage growth ratio and the blocking voltage drift across the soak. Trigger: ecss, e-st-20-08c-clause-9-6-13, protection-diode-annealing-soak, diode-annealing-arrhenius-factor, diode-forward-voltage-annealing-drift, diode-reverse-leakage-growth-ratio, protection-diode-annealing-subgroup, diode-annealing-reading-temperature-match."
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
  tags: [ecss, e-st-20-08-solar-cell-scope, e2008-diode-temperature-annealing-test, protection-diode-annealing-soak, diode-annealing-arrhenius-factor, diode-forward-voltage-annealing-drift, diode-reverse-leakage-growth-ratio, protection-diode-annealing-subgroup, diode-annealing-reading-temperature-match]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cells -- Diode Temperature Annealing Test (space-systems/ecss/e2008-diode-temperature-annealing-test)

Use when the task is clause 9.6.13 of ECSS-E-ST-20-08C -- the soak that
holds an external protection diode hot and then asks whether the device
came back out electrically where it went in. Nothing is cycled here and
nothing is vibrated. The devices are simply held at temperature long
enough for whatever is mobile inside the junction and the contacts to
move, and the whole result is a comparison between two sets of readings
taken either side of that hold.

## Domain quick reference

- The soak carries a floor and a ceiling, and they come from different
  places. The floor is the policy's: below it nothing anneals in the
  time available. The ceiling is the package's rating, and a soak above
  it anneals the encapsulant alongside the junction, so the drift that
  follows belongs to the package rather than to the diode.
- Temperature and time are one variable, not two. An Arrhenius factor
  built from the activation energy and the reciprocal temperature
  difference turns the soak into equivalent hours at the reference
  temperature, which is the only footing on which a short hot soak and a
  long warm one can be compared.
- The sample is drawn from one subgroup. Devices counted in from another
  subgroup fill the oven without filling the plan, because the
  statistics were written against the subgroup the annealing test names.
- The post-soak reading has to be taken at the same temperature as the
  pre-soak one. A device measured while it is still warm reports its
  own temperature coefficient, and that number is far larger than the
  annealing drift it would be mistaken for -- which is why a reading
  temperature mismatch outranks the drift it would otherwise produce.
- Forward voltage and blocking voltage move by a fraction of themselves,
  so a relative drift is the right measure. Reverse leakage does not: it
  spans decades, and a percentage of a nanoamp says nothing. It is
  judged as a growth ratio against where it started.
- A recovery dwell sits between the soak and the post reading. Without
  it the devices are still shedding heat, and the reading temperature
  match is satisfied on paper by a thermocouple rather than by the die.

## Workflow

1. Validate the annealing policy first: subgroup floor, soak temperature
   and duration floors, reference temperature, activation energy,
   equivalent-hours floor, recovery dwell, reading temperature gap and
   the three drift ceilings. A reference temperature sitting above the
   soak floor is refused rather than used, because such a soak
   accelerates nothing.
2. Count the devices the plan actually draws from the annealing
   subgroup, taking a label from another subgroup as zero rather than as
   a substitute, and hold the count against its floor.
3. Derive the acceleration factor and the equivalent reference hours
   before any judgement is made, and hold the soak temperature against
   both its own floor and the declared package rating.
4. Take the gap between the two reading temperatures, then the forward
   voltage drift, the reverse leakage growth ratio and the blocking
   voltage drift across the soak. A value landing exactly on a ceiling
   passes; the comparison tolerance absorbs representation error and the
   ceiling does not move.
5. Report every finding, not the first: profile, dose, dwell, sample and
   each of the three drifts.
6. Close on one verdict, in this order -- reading temperature mismatch
   (reported as a soak profile deficiency, because it invalidates the
   drift rather than being one), parameter instability, sample plan
   deficient, soak profile deficient, or annealing stability accepted.

## Pitfalls

- Reading the soak temperature against the policy floor alone. The
  package rating is the other half of the band, and a soak that clears
  the floor by overshooting the rating produces drift nobody can
  attribute.
- Treating temperature and duration as independent boxes to tick. A
  soak that meets both floors can still be worth a fraction of the
  equivalent hours asked for, and only the Arrhenius factor says so.
- Filling the oven to the device count from whatever subgroup is to
  hand. The count is a subgroup count, and a mixed load produces a
  result that belongs to no subgroup.
- Measuring the post-soak forward voltage on a device that has not come
  back to the pre-soak temperature. Around two millivolts per kelvin,
  a sixty kelvin offset is thirty times the drift the ceiling is set at,
  and the report will name it annealing.
- Expressing reverse leakage drift as a percentage. Leakage moves in
  decades, so a percentage either saturates or vanishes; the ratio is
  what carries the information.
- Skipping the recovery dwell because the chamber readout says the set
  point has been reached. The chamber is not the die, and the dwell is
  what makes the two readings comparable.
- Comparing a derived dose against its floor by bare arithmetic. The
  acceleration factor comes out of an exponential of a reciprocal
  difference, which lands a few units in the last place either side of a
  limit on different hosts, so the comparison absorbs that error while
  the floor itself is never relaxed.

## Behavior contract (gate 3)

The policy validation, the annealing subgroup device count, the
Arrhenius acceleration factor and equivalent reference hours, the
package rating check, the reading temperature gap, the forward voltage
and blocking voltage relative drifts, the reverse leakage growth ratio,
and the annealing verdict order are exercised by the gate 3 contract
test: scripts/test_e2008_diode_temperature_annealing_test.py against
scripts/e2008_diode_temperature_annealing_test_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_diode_temperature_annealing_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
