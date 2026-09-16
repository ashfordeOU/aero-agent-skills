---
name: e2008-blocking-diode-surface-finish
description: "Use when a blocking diode contact surface finish record has to become a verdict. Assess the finish the contact surfaces of a blocking diode carry at the surface finish check of ECSS-E-ST-20-08C clause 12.6.14: hold the roughness against both the ceiling the contact works at and the ceiling past which no joint onto it can be relied on, turn every anomaly into the fraction of the metallisation it eats through instead of sentencing it on appearance, accumulate coverage by kind and in total, reject a blister and a pit through to the substrate, return oxidation and residue past their allowances, and leave a device open on an under-magnified look or one polarity. Trigger: ecss, e-st-20-08c-clause-12-6-14, blocking-diode-contact-surface-finish, blocking-diode-contact-roughness-ceiling, blocking-diode-metallisation-penetration-fraction, blocking-diode-finish-anomaly-coverage, blocking-diode-finish-examination-magnification."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-blocking-diode-surface-finish, blocking-diode-contact-surface-finish, blocking-diode-contact-roughness-ceiling, blocking-diode-metallisation-penetration-fraction, blocking-diode-finish-anomaly-coverage, blocking-diode-finish-examination-magnification, blocking-diode-contact-blister-rejection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Blocking Diodes — Contact Surface Finish (space-systems/ecss/e2008-blocking-diode-surface-finish)

Use when the task is the surface finish check of ECSS-E-ST-20-08C clause
12.6.14 -- the finish quality shown by the contact surfaces of a solar
array blocking diode. The whole string current leaves the diode through
two small metallised contacts, and every joint made later -- the welded
interconnector, the soldered tab -- is made onto the finish those
contacts carry. What the check sees has to become a verdict, and the
two things it is looking at fail in opposite directions.

## Domain quick reference

- Texture and defects are separate judgements on the same contact. The
  roughness of the metallisation as a whole decides whether a weld or a
  solder joint wets and seats; discrete anomalies sitting on an
  otherwise sound finish are judged one at a time.
- Roughness needs two ceilings, not one. Below the working ceiling the
  contact is as drawn. Between the working ceiling and the bondable
  ceiling it still takes a joint but not a repeatable one, so it goes
  back for repolishing. Past the bondable ceiling nothing made onto it
  can be relied on and the device is out. Collapsing the two into a
  single limit either scraps repolishable parts or passes unbondable
  ones.
- Anomalies are not sentenced on how they look. A dark patch that is a
  film lying on intact metallisation is a cleaning job; a bright pit
  that has eaten through to the substrate has removed the conductor.
  The discriminator is penetration -- the anomaly depth as a fraction
  of the metallisation thickness it sits in -- and the same visual
  grade lands on either side of it depending on how thick that
  metallisation is.
- Coverage is the second axis and it catches what penetration misses. A
  shallow anomaly spread over most of the contact leaves no sound area
  for the joint even though nothing went through, so coverage is
  totalled per kind and again across all kinds.
- A blister needs no arithmetic. It is the finish standing off the
  metal beneath it, so adhesion has already been lost over the area it
  spans whatever its measured depth reads.
- Magnification is a precondition, not a detail. An anomaly finer than
  the examination resolved was not looked for, so a clean report from
  an under-magnified look is a clean report about nothing.
- Both polarities take a joint. A device with one contact examined is
  left open rather than sentenced from the half that was seen.

## Workflow

1. Validate the finish policy first: the magnification floor, the two
   roughness ceilings, the per-kind and total coverage allowances, the
   penetration allowance and the rework margin. A bondable ceiling at
   or below the working ceiling, or a per-kind allowance above the
   total, is refused rather than used.
2. For each contact, read the polarity, the metallisation thickness,
   the measured roughness and the magnification the examination ran at.
   A contact examined below the declared floor is marked unexamined and
   its verdict is left open.
3. Take the roughness against the bondable ceiling first and the
   working ceiling second, so an unbondable contact is rejected rather
   than sent for a repolish it cannot come back from.
4. Convert every anomaly depth into a penetration fraction against that
   contact's own metallisation thickness. A fraction at or above one
   has reached the substrate and is rejected; a blister is rejected on
   its kind alone.
5. Total the coverage per anomaly kind and across kinds, and refuse a
   record whose anomalies add up to more area than the contact has.
   Take the total against the assembly-level coverage allowance even
   when no single anomaly is over.
6. Sentence the device from the worse of its two contacts, and leave it
   open when either polarity is missing or was examined below the
   magnification floor.
7. Roll the lot up: count dispositions, take the share of devices
   carrying any finding against the lot allowance, and keep the lot
   open while any device is missing a record or left open.

## Pitfalls

- Reading a single roughness limit off the drawing and sentencing on
  it. One limit cannot separate a contact that needs repolishing from
  one that can never be joined, and the two dispositions cost very
  different amounts.
- Grading an anomaly by its visual severity. Depth only means something
  against the metallisation it sits in; the same 2 um pit is a finding
  on a 5 um contact and a scrap on a 2 um one.
- Passing a contact because every anomaly on it is individually inside
  the allowance. Coverage adds up, and a contact peppered with
  admissible marks can have no sound area left where the joint goes.
- Accepting a clean report from an examination run below the declared
  magnification. Nothing finer than the optics resolved was looked for,
  so the report is silent rather than clean.
- Sentencing a device from the contact that happened to be examined.
  The string current crosses both, and the unexamined polarity is the
  one that will fail.
- Treating a blister as a shallow defect because the depth gauge reads
  small. The depth is irrelevant; the adhesion under its whole area is
  already gone.

## Behavior contract (gate 3)

The policy validation, the penetration fraction, the per-anomaly
disposition including the blister and through-to-substrate rules, the
per-kind and total coverage accumulation with its area consistency
check, both roughness ceilings, the magnification floor, the
worse-contact device sentencing, the missing-polarity hold and the lot
roll-up with its affected-device allowance are exercised by the gate 3
contract test:
scripts/test_e2008_blocking_diode_surface_finish.py against
scripts/e2008_blocking_diode_surface_finish_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_blocking_diode_surface_finish.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
