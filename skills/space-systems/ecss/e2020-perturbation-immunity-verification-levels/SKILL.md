---
name: e2020-perturbation-immunity-verification-levels
description: "Allocate every power-bus perturbation immunity requirement to the verification level that can actually reproduce it, under ECSS-E-ST-20-20C clause 5.2.16.2.1. Use when a protection-device immunity list has to be split between unit-level bench testing and spacecraft-level testing instead of deferred whole: refuse an inverted frequency band or a repeated identifier, send to spacecraft level anything needing the flight harness, the real bus source impedance or cross-user coupling, keep the rest at the earliest representative level, name a stimulus beyond both the bench and the facility, then merge the bands actually verified and report every uncovered slice of the specified band. Trigger: ecss, e-st-20-20c-clause-5-2-16, lcl-perturbation-immunity-allocation, power-bus-unit-level-immunity-test, power-bus-spacecraft-level-immunity-test, bus-source-impedance-representativeness, flight-harness-representativeness, immunity-frequency-band-coverage."
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
  tags: [ecss, e-st-20-20-power-protection-device-scope, e2020-perturbation-immunity-verification-levels, lcl-perturbation-immunity-allocation, power-bus-unit-level-immunity-test, power-bus-spacecraft-level-immunity-test, bus-source-impedance-representativeness, flight-harness-representativeness, immunity-frequency-band-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Protection Devices -- Perturbation Immunity Verification Levels (space-systems/ecss/e2020-perturbation-immunity-verification-levels)

Use when the task is the clause 5.2.16.2.1 split of ECSS-E-ST-20-20C:
the immunity a protection device owes against the perturbations living
on its power bus has to be demonstrated, and each requirement has to be
placed at unit level or at spacecraft level before anybody can claim the
set will actually be verified.

## Domain quick reference

- The two levels are not two ways of doing the same test. Unit level is
  the device alone on a bench, driven by a laboratory source through a
  laboratory harness. Spacecraft level is the device in its flight
  position, fed by the real bus through the real harness, with the other
  users of that bus connected and running.
- Some perturbations only exist once the flight harness inductance, the
  real source impedance of the bus and the switching of the neighbouring
  users are all present together. A bench cannot manufacture them from
  a signal generator, so those requirements belong at spacecraft level
  whatever the schedule would prefer.
- Everything a bench can represent belongs on the bench. A
  spacecraft-level slot arrives late, is shared with the whole
  programme, and is the one campaign that cannot be repeated when the
  result is a surprise; a requirement pushed there for convenience buys
  a late finding at full price.
- Two failure shapes are worth keeping apart. A requirement whose
  amplitude or upper frequency is beyond the bench AND beyond the
  spacecraft-level facility is not allocated at all, and saying so is
  the point of the exercise. A slice of the specified frequency band
  that no allocated requirement reaches is a different defect: every
  individual requirement is placed, and the band still is not covered.
- What has been verified is the UNION of the allocated requirement
  bands, not the widest single band in the list. Two requirements whose
  bands touch close a span between them; two whose bands leave daylight
  do not, however wide each one is on its own.
- Bench and facility capability figures, the advisory ceiling on how
  many items may land in the spacecraft-level slot and the unit-level
  share floor are declared project policy rather than physical
  constants; the defaults in the logic module are a starting point a
  project substitutes its own values into.

## Workflow

1. Validate the requirement list: a named perturbation, a positive
   amplitude, a frequency band the right way up, boolean
   representativeness flags and unique identifiers. A requirement whose
   flags are strings cannot be allocated, so it is refused rather than
   read as true.
2. Validate the policy: a facility that reproduces less than the bench
   is not a fallback, and a share floor outside zero to one is a data
   error.
3. For each requirement, collect every reason the bench cannot
   represent it -- flight harness, bus source impedance, cross-user
   coupling, amplitude beyond the bench, upper frequency beyond the
   bench. No reasons means unit level.
4. When the bench is blocked, ask whether the spacecraft-level facility
   can raise the stimulus at all. If it can, allocate there and carry
   the blocking reasons forward so a reviewer sees why. If it cannot,
   leave the requirement unplaced and raise it as a finding.
5. Merge the frequency bands of every allocated requirement, joining
   bands that touch or overlap, and subtract the result from the
   specified band. Report each remaining slice as its own finding.
6. Report the unit-level share and the spacecraft-level count as
   advisories, so a split that is technically defensible but
   operationally top-heavy is visible before the slot is booked.

## Pitfalls

- Allocating on schedule pressure rather than representativeness. The
  question is what the level can physically reproduce; a harness-borne
  transient does not become a bench test because the bench is free.
- Treating an unplaced requirement and a band gap as the same finding.
  The first is a facility problem and is fixed by a bigger source; the
  second is a planning problem and is fixed by another requirement.
  Reporting only one of them hides the other.
- Reading the covered band off the widest requirement. Coverage is the
  union of the allocated bands, so two wide bands with daylight between
  them leave a gap that neither one reveals on its own.
- Assuming a spacecraft-level allocation is always available. The
  facility has an amplitude and a frequency limit of its own, and a
  requirement beyond both levels has to be named rather than quietly
  inherited by the later campaign.
- Comparing a stimulus amplitude against a bench capability by bare
  arithmetic. A case meant to sit exactly on the capability can land a
  few units in the last place the wrong side of it once the figures have
  been scaled; the comparison absorbs that representation error while
  the capability stays as declared.

## Behavior contract (gate 3)

The policy validation, requirement validation, bench blocker
collection, facility capability check, per-requirement allocation,
interval merging, band gap detection and the campaign verdict are
exercised by the gate 3 contract test:
scripts/test_e2020_perturbation_immunity_verification_levels.py against
scripts/e2020_perturbation_immunity_verification_levels_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2020_perturbation_immunity_verification_levels.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
