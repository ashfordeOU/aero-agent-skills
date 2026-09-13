---
name: e2007-mounting-isolator-representation
description: "Use when verify that a unit whose flight installation sits on isolating mounting hardware is presented to an electromagnetic-compatibility test on a representative mounting base under ECSS-E-ST-20-07C clause 5.2.6.3: categorize the flight mounting-base as hard-mounted, isolator-mounted or stand-off-mounted, require an isolator-mounted unit to keep the same isolator-family, isolator count and stack-height on test, compute the direct-current resistance the isolator stack leaves between unit-chassis and mounting-base, check the dedicated bonding-strap that restores the chassis-reference across a dielectric isolator, and raise a finding when the flight mounting-hardware is neither known nor bounded by a declared worst-case. Trigger: ecss, e-st-20-07c, mounting-isolator, isolator-mounted-unit, mounting-base-representativeness, isolator-stack-resistance, bonding-strap-resistance, chassis-reference-path, emc-test-setup."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-mounting-isolator-representation, mounting-isolator, isolator-mounted-unit, mounting-base-representativeness, isolator-stack-resistance, bonding-strap-resistance, chassis-reference-path]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electromagnetic Compatibility — Mounting Isolator Representation (space-systems/ecss/e2007-mounting-isolator-representation)

Use when the task is the isolator-representativeness rule of
ECSS-E-ST-20-07C clause 5.2.6.3 -- showing that a unit which flies on
isolating mounting hardware is bolted down for an
electromagnetic-compatibility run on a mounting base carrying that same
hardware, instead of being hard-mounted flat to the bench plane because
the isolators were awkward to fit.

## Domain quick reference

- The mounting hardware is part of the unit's return path, not a
  mechanical detail. Isolating feet insert a real interface impedance
  between the unit chassis and the mounting panel, and that impedance
  reshapes conducted emission, common-mode current division and
  radiated coupling. Removing it for convenience makes the bench result
  optimistic in the emission direction and unrepresentative in the
  susceptibility direction.
- Three mounting arrangements are distinguished. Hard-mounted: the unit
  feet make direct metal-to-metal contact with the panel and the
  mounting interface itself is the chassis-reference. Isolator-mounted:
  vibration or shock isolators sit between foot and panel, with a stack
  height and an isolator count that both matter. Stand-off-mounted: the
  feet are lifted on spacers with no isolating element. The categories
  are decided from the declared hardware, and an arrangement the record
  cannot support is rejected rather than guessed.
- Isolator families split by whether they leave a direct-current
  chassis path at all. An elastomeric or dielectric-washer isolator is
  effectively an open circuit at direct current, so the unit chassis
  is floating unless a dedicated bonding-strap is fitted alongside it.
  A wire-rope or conductive-elastomer isolator does carry current, and
  its stack resistance falls as the isolator count rises because the
  feet sit electrically in parallel.
- A bonding-strap is graded on two properties, not one. Its
  direct-current resistance must sit under the interface limit, and its
  length-to-width aspect ratio must stay low, because a long narrow
  strap is inductive and stops being a bond well below the frequencies
  the run is meant to cover.
- Representativeness has a fallback: where the flight mounting
  arrangement is genuinely not yet fixed, a declared worst-case
  arrangement may stand in for it. An arrangement that is neither known
  nor bounded by such a declaration is a finding in itself, not a pass.

## Workflow

1. Categorize the flight mounting-base and the test mounting-base from
   their declared hardware: isolator count and isolator-family, or
   stand-off height, or neither. Reject a record whose isolator count
   and isolator-family disagree, or whose isolator stack height is
   missing.
2. Confirm the flight arrangement is known, or that a worst-case
   arrangement has been declared to bound it. Where neither holds,
   record the finding and continue the comparison on what was declared.
3. Compare the two categories. A category mismatch -- most often an
   isolator-mounted flight unit hard-mounted on the bench -- ends the
   comparison there, because the remaining hardware properties no
   longer describe the same interface.
4. Within a matching isolator-mounted pair, compare isolator-family,
   isolator count, and stack height against the tolerance fraction the
   setup declares.
5. Compute the isolator stack resistance for the test arrangement from
   the family's single-isolator interface resistance divided by the
   isolator count, and decide whether the stack still offers a
   direct-current chassis path.
6. Where the stack offers no such path, require a dedicated
   bonding-strap and grade it: compute its resistance from resistivity,
   length and cross-section, compute its length-to-width aspect ratio,
   and check both against their limits. Grade a strap fitted alongside
   a conducting stack the same way.
7. Aggregate the findings. The setup is representative only when the
   finding list is empty.

## Pitfalls

- Reading a hard-mount as the conservative choice. It is not
  conservative in either direction: it lowers the chassis-to-panel
  impedance the flight build actually has, so emission is understated
  and the injected-current distribution in a susceptibility run is
  wrong.
- Counting isolators without the family. Four wire-rope isolators and
  four elastomeric isolators give the same count and opposite
  electrical behaviour -- one is a parallel low-resistance chassis
  path, the other is an open circuit.
- Fitting a bonding-strap and checking only its resistance. A strap
  whose length-to-width ratio is high passes a milliohm-meter and still
  fails as a bond, because the inductance dominates over most of the
  measured band.
- Treating an unset flight arrangement as an implicit hard-mount. An
  arrangement that was never captured is an open representativeness
  question; the declared worst-case is the only way to close it without
  the real hardware.
- Comparing stack height in absolute millimetres against a fixed
  allowance. The allowance is a fraction of the flight stack height, so
  a tall isolator stack legitimately carries a wider absolute band than
  a short one.

## Behavior contract (gate 3)

The mounting-base categorization, isolator-stack resistance,
chassis-path decision, bonding-strap grading and aggregate
representativeness logic is exercised by the gate 3 contract test:
scripts/test_e2007_mounting_isolator_representation.py against
scripts/e2007_mounting_isolator_representation_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_mounting_isolator_representation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
