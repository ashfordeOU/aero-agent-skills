---
name: q7031-paint-process-qualification
description: "Validate that a painting process and the facility running it are qualified to coat flight hardware. Use when a booth, a material and a crew have to be signed off together before production spraying: size the witness coupon set the coating application owes, grade every process parameter against its qualified window, grade the booth environment including particulate class and the dew-point margin the substrate holds over the air, check that the operators who sprayed the coupons were still certified, and date the qualification so an expired one cannot quietly keep producing. Trigger: ecss, q-st-70-31c-painting-scope, painting-process-qualification, paint-facility-environmental-envelope, paint-booth-dew-point-margin, painting-witness-coupon-set, paint-operator-certification-currency."
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
  tags: [ecss, q-st-70-31c-painting-scope, q7031-paint-process-qualification, painting-process-qualification, paint-facility-environmental-envelope, paint-booth-dew-point-margin, painting-witness-coupon-set, paint-operator-certification-currency]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Painting — Process Qualification (space-systems/ecss/q7031-paint-process-qualification)

Use when the task is the process-control qualification of ECSS-Q-ST-70-31C: a
paint, a set of application parameters, a booth and the people who run it are
being signed off as one qualified process, with witness coupons as the
evidence, before any flight hardware is sprayed.

## Domain quick reference

- The qualification is of the whole process, not the paint. The same material
  sprayed in a different booth, at a different gun distance, by an uncertified
  operator is a different process and is not covered by the certificate on the
  wall.
- Coupons are the evidence and the set is sized by what the coating is for.
  Every application owes adhesion, dry-film thickness, outgassing and humidity
  resistance; a thermal-control finish adds thermo-optical and thermal-cycling
  coupons; a conductive finish adds surface resistivity and cycling. A missing
  kind is a hole in the qualification, while a short count of a kind present is
  a condition on it.
- Process parameters are pinned to windows, not to nominals: spray pressure,
  gun distance, pass count, flash-off, cure temperature and cure duration. A
  parameter with no recorded value and a parameter with no window are two
  different findings and both matter.
- The booth envelope is air temperature, relative humidity, air velocity and
  particulate class. All four are conditions the coupons were produced under,
  so a production run outside them is outside the qualification.
- The dew-point margin is the one environmental number that is computed rather
  than read. The dew point follows from booth air temperature and humidity,
  and the margin is how far the substrate sits above it. A substrate at or
  below the dew point is condensing, and paint applied onto condensate has no
  adhesion whatever the gun settings were.
- Currency runs on two clocks. Operators carry a certification validity, and
  the qualification itself carries one; a month-end grant clamps to the
  shorter month at expiry rather than rolling forward and quietly gaining a
  day.

## Workflow

1. Take the coating application and derive the coupon kinds it owes, then
   grade the coupon set for absent kinds and short counts separately.
2. Grade each process parameter against its qualified window, treating both
   edges as inside, and raise unrecorded values and absent windows as their
   own findings.
3. Grade the booth environment against its envelope, and grade the particulate
   class against its limit.
4. Compute the dew point from booth air temperature and humidity, take the
   margin the substrate holds over it, and put that against the floor. Raise
   an unevaluated margin rather than assuming one.
5. Check each operator's certification against the reference day, where a
   certification running to its expiry day is still current.
6. Date the qualification from the grant day and its validity, and raise an
   expired qualification.
7. Issue the state: qualified with no findings; not qualified where a coupon
   kind, a parameter, the environment, the dew point or the date failed;
   conditionally qualified where only evidence depth is short. Aggregate
   across the facility set.

## Pitfalls

- Treating a material qualification as a process qualification, so the same
  paint in a second booth inherits a certificate that never covered it.
- Recording parameters as nominals with no window behind them, which makes a
  production deviation unarguable in either direction.
- Reading relative humidity as the moisture check and never computing the dew
  point, which is the number that says whether the part is condensing.
- Measuring the air temperature and assuming the substrate matches it, when a
  part brought in cold sits well below the booth air for hours.
- Counting coupons without checking their kinds, so a set of twenty coupons
  can still be missing the thermo-optical evidence entirely.
- Letting an operator certification lapse mid-campaign and carrying the
  coupons they sprayed as qualification evidence.

## Behavior contract (gate 3)

The coupon sizing and coverage, parameter windows, environmental envelope,
particulate class, dew-point margin, operator currency, month-clamped expiry
dates and the qualification state are exercised by the gate 3 contract test:
scripts/test_q7031_paint_process_qualification.py against
scripts/q7031_paint_process_qualification_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q7031_paint_process_qualification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
