---
name: e20-electrical-bonding-conformance
description: "Use when verify that the bonding of spacecraft structure and equipment meets the electromagnetic design provisions referenced by ECSS-E-ST-20C clause 6.3.8.1: categorize each bond by the function it performs, take the resistance window that function imposes, compute a strap's direct-current resistance from its geometry and contact interfaces, check a radio-frequency reference bond for strap length-to-width ratio and impedance at the frequency of interest, screen the dissimilar-metal couple against the environment it will see, and bound the conductor heating a fault or surge current produces. Trigger: ecss, e-st-20c-clause-6-3-8-1, electrical-bonding-conformance, bond-resistance-window, bond-strap-inductance, radio-frequency-bond-reference, electrostatic-charge-bleed-path, galvanic-couple-compatibility, fault-current-return-path."
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
  tags: [ecss, e-st-20-electrical-scope, e20-electrical-bonding-conformance, electrical-bonding-conformance, bond-resistance-window, bond-strap-inductance, radio-frequency-bond-reference, electrostatic-charge-bleed-path, galvanic-couple-compatibility, fault-current-return-path]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Electrical Bonding Conformance (space-systems/ecss/e20-electrical-bonding-conformance)

Use when the task is the clause 6.3.8.1 bonding provision of
ECSS-E-ST-20C -- showing that structure and equipment are bonded in
line with the electromagnetic design clauses the standard points at,
rather than merely that a continuity check passed somewhere.

## Domain quick reference

- Bonding is not one requirement, it is four with different physics.
  Each bond is categorized once by the function it performs and that
  category, not the hardware, sets the acceptance window. A
  fault-current or structure-current return and a radio-frequency
  reference or shield termination both demand a few milliohms of
  direct-current resistance. A lightning down conductor, a launcher
  umbilical bond and an equipment mounting face or panel joint are
  allowed an order more. An electrostatic charge-bleed path is the
  odd one out: it has a window with a floor as well as a ceiling,
  because a path that is too conductive defeats the isolation it sits
  next to while a path that is too resistive never bleeds the charge.
- The direct-current resistance of a bond strap is the bulk term --
  resistivity times length over cross-section -- plus the contact
  resistance of every mechanical interface in the path, counted once
  per joint. On a short strap the joints usually dominate the bulk
  term, which is why surface preparation and torque decide the
  measurement far more often than the strap's cross-section does.
- A radio-frequency reference bond is judged on impedance, not
  resistance. A strap has inductance that grows with length and falls
  only logarithmically with width, so a long thin strap is a poor
  reference however low its direct-current resistance reads. The
  classical geometry rule keeps the length-to-width ratio at or below
  five; the impedance at the frequency of interest is the resistance
  and the strap reactance combined in quadrature.
- A bond joins two metals, so it is also a galvanic couple. The
  difference between the two anodic indices must stay inside the limit
  for the environment the joint will actually see: a joint that is
  acceptable in a controlled dry compartment can be unacceptable in
  humid launch-site air, and the environment is part of the
  requirement, not a caveat on it.
- A bond that carries fault or surge current is finally a thermal
  part. The energy the current deposits in the bond resistance over
  the protection's clearing time raises the bond temperature by that
  energy over its thermal mass; a bond that is electrically compliant
  can still exceed the allowed temperature rise and open the very
  path the protection depends on.

## Workflow

1. Categorize each bond by the function it performs and reject a bond
   kind that is not a recognized bonding function.
2. Take the resistance window for that category -- a ceiling for the
   conductive categories, a floor and a ceiling for the charge-bleed
   path.
3. Establish the bond resistance: the measured value when one is on
   record, otherwise the computed bulk term from resistivity, length
   and cross-section plus the contact resistance of each joint.
4. Flag a resistance above the ceiling, and for a charge-bleed path
   also a resistance below the floor.
5. For a radio-frequency reference bond, compute the strap
   length-to-width ratio and the strap impedance at the frequency of
   interest; flag a ratio above the geometry limit and an impedance
   above the bond's own limit.
6. Screen the dissimilar-metal couple: look up both anodic indices,
   take the difference and flag a couple above the limit for the
   declared environment.
7. For a current-carrying bond, compute the temperature rise from the
   fault or surge current, the bond resistance, the clearing time and
   the bond's thermal mass; flag a rise above the allowed value.
8. Aggregate the resistance, impedance, galvanic and thermal findings;
   the bond conforms only when all four lists are empty.

## Pitfalls

- Accepting a continuity buzz as a bond measurement. The requirement
  is a resistance inside a window, and a low-current continuity check
  cannot resolve the milliohms the conductive categories live in.
- Applying one resistance limit to every bond. A mounting-face bond
  judged against the fault-return ceiling is over-specified, and a
  charge-bleed path judged against it is simply wrong -- that path
  has a floor as well.
- Reading a charge-bleed path as "the lower the better". Below the
  floor the path shorts out the isolation it was installed beside,
  which is a design failure, not a conservative margin.
- Judging a radio-frequency reference on its direct-current
  resistance. Strap inductance, driven by the length-to-width ratio,
  is what sets the impedance at frequency, and a compliant milliohm
  reading on a long thin strap says nothing about it.
- Ignoring the bulk term because the joints dominate, or ignoring the
  joints because the strap is thick -- both terms belong in the
  computed resistance, and which one dominates changes with geometry.
- Screening a galvanic couple against a single fixed limit. The
  allowable index difference depends on the environment the joint is
  exposed to, including ground handling, and the tightest environment
  in the life profile is the one that governs.
- Stopping at the electrical checks on a fault-current bond. The
  clearing-time energy has to fit inside the bond's thermal mass, or
  the protection path degrades on the first fault it clears.

## Behavior contract (gate 3)

The bond categorization, resistance-window, strap-resistance,
strap-inductance and impedance, length-to-width ratio, galvanic-couple
and fault-heating logic is exercised by the gate 3 contract test:
scripts/test_e20_electrical_bonding_conformance.py against
scripts/e20_electrical_bonding_conformance_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e20_electrical_bonding_conformance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
