---
name: e2001-single-carrier-margin-overview
description: "Use when determine the single-carrier multipactor-margin scheme of ECSS-E-ST-20-01C clause 4.6.1 for a radio-frequency unit: categorize every operating condition as continuous-wave or pulsed-carrier, reduce it to the governing carrier-power the multipactor-margin applies to, screen a pulsed condition against the discharge-build-up-time so a build-up-limited short-pulse is flagged rather than silently credited, convert the multipactor-threshold-power into an achieved decibel multipactor-margin, then compare that against the nominal value owed by the selected verification-route, keeping the analysis-margin family apart from the multipactor-test-margin family. Trigger: ecss, e-st-20-electrical-scope, single-carrier-multipactor, continuous-wave-operation, pulsed-carrier-operation, multipactor-margin, multipactor-threshold-power, discharge-build-up-time, margin-budget-overview."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-single-carrier-margin-overview, single-carrier-multipactor, continuous-wave-operation, pulsed-carrier-operation, multipactor-margin, multipactor-threshold-power, discharge-build-up-time]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Single-Carrier Multipactor Margin Overview (space-systems/ecss/e2001-single-carrier-margin-overview)

Use when the task is the margin scheme introduced by ECSS-E-ST-20-01C
clause 4.6.1 -- the numerical multipactor-margin that a single-carrier
radio-frequency unit owes, how that number is expressed, and how a
continuous-wave condition and a pulsed-carrier condition each reduce to
the one carrier-power the margin is taken against.

## Domain quick reference

- A multipactor-margin is a ratio, not an absolute level: it is the
  decibel distance between the multipactor-threshold-power of a gap
  (the lowest carrier-power at which the resonant-electron discharge
  sustains itself) and the highest carrier-power that gap ever sees in
  operation. Ten times the base-ten logarithm of the threshold-to
  -operating ratio gives the achieved value; a margin of six decibel
  means the threshold sits four times above the operating point.
- Single-carrier operation carries one modulated carrier through the
  gap, so the envelope is either continuous-wave (one steady level,
  and the carrier-power is that level) or pulsed-carrier (a duty-cycled
  envelope, and the governing quantity is the peak-envelope-power, not
  the duty-averaged value). Reducing a pulsed condition to its average
  understates the field in the gap by the reciprocal of the duty-cycle
  and is the single most common error in this clause.
- A pulsed condition has one relaxation the continuous-wave case does
  not: the discharge needs a finite number of radio-frequency cycles
  for the seed electron population to multiply up to a detectable
  level. Divide that cycle count by the carrier frequency and the
  result is the discharge-build-up-time. A pulse shorter than the
  build-up-time cannot let the discharge grow to a measurable level --
  but that is a justification to be substantiated with the seeding and
  yield assumptions on record, never an automatic credit.
- Two margin families sit under this clause and must not be mixed: the
  analysis-margin owed when the case is closed by modelling alone, and
  the multipactor-test-margin owed when the case is closed by a seeded
  campaign on hardware. Each family carries its own nominal decibel
  value per carrier mode, and a project margin-policy table holds those
  values so a unit is never graded against a number that was not
  declared up front.

## Workflow

1. Inventory every multipactor-critical gap and, for each, every
   operating condition it is exposed to. Reject an unrecognized
   carrier mode before it enters the budget.
2. Reduce each condition to its governing carrier-power: the steady
   level for a continuous-wave condition, the peak-envelope-power for
   a pulsed-carrier condition, deriving that peak from the duty-cycle
   when only the duty-averaged level is on record.
3. For a pulsed condition with a seeding and yield model on record,
   compute the discharge-build-up-time from the per-cycle growth of
   the electron population and compare it with the pulse width; flag a
   build-up-limited short-pulse as a finding carrying a justification
   obligation, not as a pass.
4. Compute the achieved multipactor-margin of each condition from the
   gap's multipactor-threshold-power and the governing carrier-power.
5. Look up the nominal value owed from the margin-policy table for the
   condition's margin family and carrier mode, and compare. Treat an
   exactly-met requirement as met -- the comparison runs to a declared
   representation tolerance so a logarithm landing a few units in the
   last place low is not read as a shortfall.
6. Roll the conditions up per unit: report the worst shortfall, the
   non-compliant conditions and every build-up finding. The unit is
   not margin-compliant until the shortfall list is empty.

## Pitfalls

- Taking a pulsed condition's duty-averaged level as the operating
  point -- the gap sees the peak-envelope-power, and the error grows
  as the duty-cycle falls.
- Reading "the pulse is shorter than the build-up-time" as compliance.
  The build-up model rests on an assumed seed population and per-cycle
  growth; without both on record the short-pulse argument has no basis
  and the condition is still owed its full nominal value.
- Crediting a multipactor-test-margin value against a case closed by
  modelling alone. The two families exist because a seeded campaign
  bounds different uncertainties than a model does; swapping the
  numbers silently under-margins the unit.
- Comparing a linear power ratio against a decibel requirement, or
  comparing the margin against the threshold instead of against the
  nominal requirement -- the requirement is a distance, so both sides
  of the comparison have to be in decibel.
- Grading a unit against a margin-policy value that was never declared
  for the project. An unset policy entry is a finding, not a default.

## Behavior contract (gate 3)

The carrier-mode reduction, discharge-build-up screening, decibel
multipactor-margin computation and nominal-requirement comparison are
exercised by the gate 3 contract test:
scripts/test_e2001_single_carrier_margin_overview.py against
scripts/e2001_single_carrier_margin_overview_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2001_single_carrier_margin_overview.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
