---
name: e2008-blocking-diode-pull-test
description: "Evaluate the interconnector adherence and bond strength the contacts of a blocking diode show when pulled, under ECSS-E-ST-20-08C clause 12.6.16: refuse a grip dragged past the off-normal cap, resolve each pull onto the contact normal and divide it by the bonded area that carried it, derive the ribbon's own tensile capacity and the share of it the pull reached, separate a bond release from a ribbon fracture, a metallisation lift and a die fracture, credit a ribbon break above the requirement as a lower bound but repeat one below it, sentence each device by its weaker contact, and hold a lot sampled too thin. Use when a blocking diode interconnector pull run is planned or its records reviewed. Trigger: ecss, e-st-20-08c-clause-12-6-16, blocking-diode-interconnector-pull, blocking-diode-contact-bond-strength, blocking-diode-pull-failure-mode, blocking-diode-ribbon-tensile-utilisation, blocking-diode-pull-off-normal-angle."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-blocking-diode-pull-test, blocking-diode-interconnector-pull, blocking-diode-contact-bond-strength, blocking-diode-pull-failure-mode, blocking-diode-ribbon-tensile-utilisation, blocking-diode-pull-off-normal-angle, blocking-diode-pull-lot-sentencing]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Blocking Diodes — Interconnector Pull Test (space-systems/ecss/e2008-blocking-diode-pull-test)

Use when the task is the pull test of ECSS-E-ST-20-08C clause 12.6.16 --
the adherence of the interconnector on a solar array blocking diode's
contacts, assessed by pulling on it. The interconnector is the ribbon
that carries the string current off the diode, welded or soldered to
the diode's metallised contact. The test takes hold of that ribbon and
pulls until something lets go, and the whole value of the record turns
on what that something was.

## Domain quick reference

- A pull record is only a bond measurement when the bond is what
  released. Four things can give way -- the bond interface, the ribbon
  itself, the metallisation lifting off the die, and the die
  fracturing -- and only the first is the measurement the clause asks
  for.
- A ribbon fracture is a censored reading, not a failed test. The bond
  never released, so its strength is known only to be at least the
  force reached. Above the required force that is enough: the bond is
  proven strong enough and the device passes on a lower bound. Below
  it nothing is proven and the pull has to be repeated on a device
  whose ribbon can carry the load.
- The ribbon's own capacity is computable and belongs in the record.
  Its cross-section times the tensile strength of its material gives
  the force it can carry, and the pull's share of that capacity says
  whether the run was ever going to reach the bond at all.
- A metallisation lift is not a weld finding. The weld held and the
  contact finish underneath it gave way, so it points back at the
  contact rather than at the bonding schedule.
- The pull direction is part of the number. A grip dragged off the
  contact normal puts only the cosine of its angle into the joint along
  the axis the requirement is written for and peels it with the rest.
  Past a declared angle the reading is not comparable with the
  requirement and the record is refused rather than corrected.
- Force does not compare across contact sizes. The normal force divided
  by the bonded area that carried it is the stress the joint actually
  saw, and a generous force on a large footprint can be a weak joint.
- Both contacts carry a ribbon. A device sentenced from one of them is
  sentenced from half the evidence, and the contact that was not pulled
  is the one that lets go in the panel.
- A lot is sentenced from a sample, so the share of the population
  actually pulled is part of the verdict rather than a footnote.

## Workflow

1. Validate the pull policy first: the minimum force, the minimum bond
   stress, the off-normal angle cap, the ribbon utilisation ceiling,
   the review margin and the sampling floor. An angle cap at ninety
   degrees, or a sampling floor of zero, is refused rather than used.
2. For each pulled contact, read the polarity, the force reached, the
   angle it was pulled at, the bonded area and the interconnector's
   dimensions and material strength.
3. Take the angle against the cap before anything else. A pull past the
   cap yields no usable number, so the contact is left open rather than
   sentenced on a resolved force nobody can compare.
4. Resolve the force onto the contact normal by its cosine, divide by
   the bonded area to get the stress the joint saw, and take the force
   reached against the ribbon's own computed capacity.
5. Branch on what released. A die fracture and a metallisation lift are
   rejections. A ribbon fracture is credited as a lower bound if it
   already cleared the requirement and otherwise sends the pull back. A
   bond release is sentenced on force and stress against their floors,
   with a review band between the requirement and the floor.
6. Flag a bond release that came at most of the ribbon's capacity: the
   run was measuring the ribbon and the bond together, and the margin
   it reports is not the bond's alone.
7. Sentence the device from the weaker of its two contacts and leave it
   open when either polarity is missing or produced no usable reading.
8. Roll the lot up: hold the pulled share against the sampling floor,
   take the count of devices that did not clear the requirement against
   the lot allowance, carry the weakest normal force in the lot, and
   keep the lot open while any device carries no usable pull.

## Pitfalls

- Writing the breaking force down as the bond strength when the ribbon
  is what broke. The bond never released; its strength is a lower bound
  and calling it a measurement overstates every joint in the lot.
- Pulling with an interconnector too weak to reach the requirement. The
  run ends in the ribbon every time and the lot accumulates records
  that prove nothing about the welds.
- Correcting an off-normal pull past the cap instead of refusing it. At
  a large angle the joint is being peeled rather than pulled, and the
  cosine no longer describes what the bond experienced.
- Comparing forces across contacts of different footprint. The larger
  contact wins on force and can be the weaker joint; the comparison
  belongs in stress.
- Reading a metallisation lift as a weld failure. The weld held. What
  gave way was the contact finish under it, which sends the
  investigation to the metallisation and not to the bonding schedule.
- Sentencing a device from whichever contact was convenient to pull.
  The string current crosses both ribbons, and the unpulled one carries
  the same load.
- Quoting a lot verdict without the sampled share beside it. A clean
  result from three devices out of six hundred is a clean result about
  three devices.

## Behavior contract (gate 3)

The policy validation, the interconnector capacity from cross-section
and tensile strength, the off-normal resolution and its angle cap, the
bond stress over bonded area, the ribbon utilisation, the four failure
mode branches including the lower-bound credit and the repeat on a
short ribbon break, the force and stress floors with their review band,
the weaker-contact device sentencing, the missing-polarity hold and the
lot roll-up with its sampling floor and failing-device allowance are
exercised by the gate 3 contract test:
scripts/test_e2008_blocking_diode_pull_test.py against
scripts/e2008_blocking_diode_pull_test_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_blocking_diode_pull_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
