---
name: e2008-ultraviolet-exposure-test-purpose
description: "Use when an accelerated ultraviolet exposure is being scoped or defended for a solar array assembly. Determine what an accelerated ultraviolet exposure must deliver before a photovoltaic assembly can be called stable under ultraviolet light, per ECSS-E-ST-20-08C clause 6.4.3.15.1: inventory the ultraviolet-sensitive elements of the stack and the degradation each one contributes, size the mission dose in equivalent sun hours from mission duration, solar distance and illuminated fraction, derive the acceleration factor the planned lamp irradiance buys, hold it under the reciprocity ceiling, and check the accumulated dose covers the mission. Trigger: ecss, e-st-20-08c-clause-6-4-3-15-1, solar-array-ultraviolet-stability, accelerated-ultraviolet-exposure-purpose, ultraviolet-equivalent-sun-hours, ultraviolet-acceleration-reciprocity-ceiling, coverglass-adhesive-ultraviolet-darkening."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-ultraviolet-exposure-test-purpose, solar-array-ultraviolet-stability, accelerated-ultraviolet-exposure-purpose, ultraviolet-equivalent-sun-hours, ultraviolet-acceleration-reciprocity-ceiling, coverglass-adhesive-ultraviolet-darkening]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Ultraviolet Exposure Test Purpose (space-systems/ecss/e2008-ultraviolet-exposure-test-purpose)

Use when the task is to state and defend why a photovoltaic assembly is
put under an accelerated ultraviolet exposure under ECSS-E-ST-20-08C
clause 6.4.3.15.1 -- which parts of the stack the exposure is meant to
prove stable, how much ultraviolet the mission will actually deliver,
and whether the planned run compresses that dose into the facility
without compressing it so hard that it stops representing the mission.

## Domain quick reference

- The ultraviolet tail of the solar spectrum is a few per cent of the
  power and most of the chemistry. Photons above roughly three electron
  volts break bonds in the organic parts of the stack, and the damage
  shows up as transmission darkening, embrittlement and an absorptance
  rise that no thermal or mechanical test will surface.
- The sensitive parts are a short list, and each one fails its own way:
  the coverglass adhesive darkens, the front-surface silicone yellows,
  the polyimide substrate embrittles and darkens, an antireflection
  coating drifts, a thermal-control paint gains absorptance, an
  ultraviolet-reject filter shifts its cutoff. A stack with none of them
  has nothing for the exposure to establish.
- The dose the mission delivers is not the mission duration. Irradiance
  falls with the square of the solar distance, and only the illuminated
  part of the orbit contributes, so a five-year low-orbit mission is
  worth a few tens of thousands of equivalent sun hours rather than
  five years of them.
- Acceleration is what makes the test finishable, and it is also the
  thing that can invalidate it. Running at many ultraviolet suns buys
  duration only while the damage tracks the accumulated dose rather than
  the rate it arrives at; past a reciprocity ceiling the sample heats,
  photoproducts stop diffusing away and the mechanism changes.
- Three numbers close the argument: the mission dose, the acceleration
  the planned lamp setting delivers, and the dose the planned run
  accumulates. A run that is inside the reciprocity ceiling but stops
  short of the mission dose has demonstrated stability against a shorter
  mission than the one being flown.
- The facility is a real constraint, not a rounding error. A low
  acceleration can push the run past what a chamber can hold open, and
  a schedule built on it fails later and more expensively than one that
  noticed at the purpose stage.

## Workflow

1. Validate the exposure policy first: the one-ultraviolet-sun
   irradiance, the significance trigger, the reciprocity ceiling and the
   facility duration limit. A ceiling below one sun is refused rather
   than used, since an accelerated run cannot be slower than the mission.
2. Group the declared ultraviolet-sensitive elements, rejecting an
   unrecognised one rather than ignoring it, and map each to the
   degradation quantity the exposure establishes. Append the shared
   stability objective whenever any element is present.
3. Size the mission dose in equivalent sun hours from the mission
   duration, the solar distance and the illuminated fraction. Report it
   whatever the verdict, because it is the number every later argument
   is measured against.
4. Decide whether the exposure is earned at all: at least one sensitive
   element present and a mission dose at or above the significance
   trigger. A dose landing exactly on the trigger earns the exposure;
   the comparison tolerance absorbs representation error and the trigger
   itself does not move.
5. When it is earned and a run is planned, derive the acceleration
   factor from the lamp irradiance, the dose the run accumulates, and
   the coverage ratio against the mission dose. Report the facility
   hours the mission dose would need at that acceleration.
6. Hold the acceleration under the reciprocity ceiling, the coverage at
   or above one, and the duration inside the facility limit.
7. Close on one verdict: stability not required, exposure not planned,
   exposure inadequate, or ultraviolet stability characterised --
   reporting every inadequacy found, not only the first.

## Pitfalls

- Reading the mission dose off the mission duration. The eclipse
  fraction and the solar distance between them can move the number by
  more than an order of magnitude, and the exposure is sized from it.
- Choosing the lamp setting to fit the schedule. Acceleration is bought
  against a reciprocity assumption, and once the run is past the ceiling
  the result describes a degradation mechanism the assembly will never
  meet in orbit.
- Treating a declared sensitive element as sufficient reason to expose.
  A mission dose below the significance trigger cannot move any of the
  degradation quantities enough to matter, and the run buys nothing but
  schedule.
- Stopping a run when the article looks unchanged. Coverage is a ratio
  against the mission dose, and a run that accumulated a fraction of it
  has qualified the assembly for a fraction of the mission.
- Reporting an acceleration factor without the dose it accumulated. The
  factor alone says how hard the lamp was driven, not whether the
  mission was reproduced, and the two are independent.
- Comparing a coverage ratio against one by bare arithmetic. It is a
  quotient of two derived doses and can land a few units in the last
  place either side of the bound, so the comparison absorbs that error
  while the bound itself is never relaxed.

## Behavior contract (gate 3)

The policy validation, the mission dose from duration, solar distance
and illuminated fraction, the acceleration factor, the accumulated dose
and coverage ratio, the reciprocity and facility-duration checks, the
element inventory and objective mapping, and the purpose verdict are
exercised by the gate 3 contract test:
scripts/test_e2008_ultraviolet_exposure_test_purpose.py against
scripts/e2008_ultraviolet_exposure_test_purpose_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_ultraviolet_exposure_test_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
