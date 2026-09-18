---
name: e2007-power-lead-susceptibility-procedure
description: "Execute the stepped injection run of a power-lead susceptibility test. Use when the task is ECSS-E-ST-20-07C clause 5.4.7.4 and a supply-lead disturbance has to be applied while the unit is watched for a response: hold the warm up against the longer of a floor and the declared stabilization time, walk the geometric frequency ladder across the band, derive the dwell each step needs from the slowest response the unit can show, ramp the level no more coarsely than the allowance until the required level or the drive limit is reached, and take the lowest responding level as the threshold to margin against the requirement. Refuses a record that recovers above its threshold and a response outside the ramp applied. Trigger: ecss, e-st-20-07c, power-lead-susceptibility-procedure, stepped-injection-ladder, injection-warm-up, injection-step-dwell, susceptibility-threshold-margin, drive-limited-step, level-ramp-coarseness."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-07c, e2007-power-lead-susceptibility-procedure, stepped-injection-ladder, injection-step-dwell, susceptibility-threshold-margin, drive-limited-step, level-ramp-coarseness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Power-Lead Susceptibility Injection Procedure (space-systems/ecss/e2007-power-lead-susceptibility-procedure)

Use when the task is the procedure of ECSS-E-ST-20-07C clause 5.4.7.4 --
the warm up that precedes a supply-lead susceptibility run and the stepped
injection carried out afterwards, with the unit watched for a response at
every step.

## Domain quick reference

- The run starts only after the unit has stabilized. The warm up is held
  against the LONGER of a general floor and whatever stabilization time
  the unit declares for itself: a unit that needs longer than the floor
  sets its own requirement, and a unit that needs less still waits the
  floor out.
- The frequency ladder is geometric, not linear. Points are spread a
  fixed number to the decade, so the ratio between adjacent rungs is
  constant and the low end of the band is sampled as finely, in relative
  terms, as the high end. A ladder with too few points to the decade
  steps straight over a narrow response.
- The ladder has to reach both ends of the band. A run that starts above
  the bottom or stops below the top leaves frequencies at which nothing
  was injected, and no result covers them.
- The dwell at a step is set by the unit, not by the schedule. It is the
  larger of a floor and a multiple of the slowest response the unit can
  show, because a response that takes seconds to appear is invisible at a
  step held for a fraction of one.
- The level is ramped up to the required level, never applied in one
  jump. A coarse rise can pass straight through the level at which the
  unit first responds, so the threshold recorded is higher than the real
  one and the margin is overstated.
- A ramp may stop early for exactly two reasons: the required level was
  reached, or the drive limit of the chain was reached first. A ramp that
  stopped short with neither reason declared is an incomplete step, not a
  passing one.
- The threshold is the LOWEST level at which the unit responded. A record
  in which the unit responds and then recovers at a higher level is a
  contradiction in the record, not a second threshold, and it is refused
  rather than reported.
- The margin is the threshold measured from the required level, and it
  has a requirement of its own. A threshold a decibel above the required
  level is above it and still short of the margin.
- A bound met exactly is met. A ratio of two frequencies or a difference
  of two levels can land a few units in the last place outside an
  exactly-met bound; absorb that in the comparison, never by widening the
  bound.

## Workflow

1. Check the warm up against the longer of the floor and the declared
   stabilization time, and record which of the two governed.
2. Check the ladder density: points to the decade at or above the
   minimum, otherwise report the run as stepping too coarsely.
3. Normalize each injection step: frequency, required level, the ramp of
   applied levels, the dwell, the response time, whether the drive limit
   was reached and the level any response appeared at. Reject an unknown
   key, a missing key, a ramp that does not rise and a response level
   outside the ramp that was applied.
4. Check the ramp coarseness at each step and the dwell against what the
   response time requires.
5. Where no response appeared, confirm the ramp reached the required
   level, or that a drive limit is declared to explain why it did not.
6. Where a response appeared, take the lowest responding level as the
   threshold, measure the margin from the required level, and report both
   a threshold below the required level and a margin short of its
   requirement.
7. Walk the ladder: flag a step that does not advance in frequency and
   check every genuine step against the ratio the ladder density allows.
8. Check that the first and last steps reach the bottom and the top of
   the band.
9. Aggregate: report the conforming fraction of the steps, the
   susceptible count and the drive-limited count, and accept the run only
   when no finding remains.

## Pitfalls

- Starting the injection at the floor warm up when the unit declared a
  longer stabilization time, which puts the first decade of the run on a
  unit that has not settled.
- Spreading the ladder linearly across the band, which oversamples the
  top decade and steps over narrow responses at the bottom.
- Holding a fixed short dwell at every step regardless of how slowly the
  unit can respond, so a real response appears after the injection has
  already moved on.
- Applying the required level in one jump, recording no response, and
  reporting a threshold that was never searched for.
- Reading a ramp that stopped short as a pass when no drive limit was
  declared to explain the stop.
- Taking the highest responding level, or the level the operator
  happened to notice, as the threshold rather than the lowest one.
- Treating a record that recovers at a higher level as a second
  threshold; the record contradicts itself and has to be repeated.
- Reporting a threshold above the required level as a pass when the
  margin requirement has not been met.

## Behavior contract (gate 3)

The warm-up check, the geometric ladder and its step ratio, the dwell
derived from the response time, the level-ramp coarseness, the
drive-limit and required-level reasoning, the threshold and margin
derivation, the step and profile validation and the whole-run verdict are
exercised by the gate 3 contract test:
scripts/test_e2007_power_lead_susceptibility_procedure.py against
scripts/e2007_power_lead_susceptibility_procedure_logic.py (stdlib
unittest, offline). Run:

python3 scripts/test_e2007_power_lead_susceptibility_procedure.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
