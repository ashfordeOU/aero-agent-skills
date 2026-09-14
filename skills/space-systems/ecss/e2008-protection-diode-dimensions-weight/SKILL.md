---
name: e2008-protection-diode-dimensions-weight
description: "Verify a protection diode against the lateral outline, thickness, contact geometry and interconnector placement requirements of ECSS-E-ST-20-08C clause 9.6.3: put each measured feature inside its own plus and minus band and name the state, combine the two axis offsets of every attachment point into one diametrical true-position value, judge the contact pad against the footprint it must cover and the string current it must carry, and cross-check the weighed mass against the mass the outline and material density already imply before any band is believed. Use when a protection diode measurement sheet has to be judged against the procurement drawing. Trigger: ecss, e-st-20-08c-clause-9-6-3, protection-diode-outline-tolerance-band, protection-diode-thickness-band, protection-diode-contact-pad-geometry, protection-diode-interconnector-true-position, protection-diode-mass-density-crosscheck."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-protection-diode-dimensions-weight, protection-diode-outline-tolerance-band, protection-diode-thickness-band, protection-diode-contact-pad-geometry, protection-diode-interconnector-true-position, protection-diode-mass-density-crosscheck]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Protection Diode Dimensions and Weight (space-systems/ecss/e2008-protection-diode-dimensions-weight)

Use when the task is to decide whether a delivered protection diode is
dimensionally the part the array was laid out around under
ECSS-E-ST-20-08C clause 9.6.3 -- lateral size, thickness, the contact
geometry the attachment lands on, and where the interconnector
attachment point actually sits.

## Domain quick reference

- Four families of feature carry the clause. The lateral outline sets
  the layout, the stay-out zone and the bonding footprint. The
  thickness sets the stack height under the coverglass and is the term
  the mass follows most directly. The contact geometry decides whether
  the attachment can be made at all and whether it can pass the string
  current. The interconnector placement decides whether the attachment
  lands where the harness expects it.
- Every dimensional feature is judged inside its own plus and minus
  band, and the direction of the departure is part of the answer: a
  diode running long is a different layout problem from one running
  short, and both differ from one that fits.
- A tolerance written as a subtraction rarely lands on the limit the
  drawing means. Nominal 0,18 minus 0,02 is not 0,16 in binary, so a
  part measuring exactly the drawn limit must not be refused by the
  arithmetic that checks it.
- Attachment offsets are not judged one axis at a time. A point inside
  the per-axis allowance on both axes can still sit outside the round
  zone the drawing permits, which is why the offsets are combined into
  one diametrical true-position value and that value is compared.
- The contact pad carries two separate requirements that a single area
  number has to satisfy at once: enough of the footprint to be bonded
  reliably, and enough area that the string current does not turn the
  attachment into the hot spot of the string.
- Mass is not an independent measurement. Outline, thickness and
  declared material density already imply it, so a weighed mass that
  disagrees with the implied mass means one of the two came off a
  different part.
- A diode cannot be machined back to size. An out-of-band feature is a
  procurement outcome, not a rework instruction, so the departure is
  reported with its state rather than absorbed.

## Workflow

1. Validate the acceptance policy first: contact coverage floor,
   current-density ceiling, true-position zone and mass crosscheck
   tolerance. A mass tolerance that would admit a part of any mass is
   refused rather than used.
2. Take each dimensional feature in turn, derive its band from the
   nominal and the two tolerances, and name the state as in-band,
   under-band or over-band. A feature landing exactly on a limit is
   in-band; the comparison tolerance absorbs representation error and
   the limit does not move.
3. Derive the footprint from the measured lateral dimensions, not the
   nominal ones, because the pad has to cover the diode that arrived.
4. Take the contact pad through both of its duties: coverage of that
   footprint, and current density at the declared string current. A pad
   measuring larger than the footprint is refused as a measurement
   error rather than reported as generous coverage.
5. Combine each attachment point's two axis offsets into one
   true-position value and keep the worst point, because the harness
   fits the worst one.
6. Derive the implied mass from the measured outline, thickness and
   declared density, and compare it with the weighed mass before any
   band is believed.
7. Close on one verdict: dimensions conforming, outline out of band,
   contact geometry inadequate, attachment out of position, or mass
   inconsistent -- reporting every departure found, not only the one
   that names the verdict.

## Pitfalls

- Checking attachment offsets axis by axis. Both axes inside their
  allowance is not the same statement as the point being inside the
  round zone, and the combined value is the larger of the two numbers
  every time the point is off both axes.
- Deriving the footprint from the drawing nominal. The pad has to cover
  the part that arrived; a diode at the short end of its band has a
  smaller footprint and a better coverage fraction than the drawing
  suggests.
- Reading the contact pad as one requirement. An area that covers
  enough of the footprint to bond can still stand far too small for the
  string current, and the two limits fail in opposite directions.
- Treating the mass as a separate acceptance line. It is a crosscheck
  on the outline: a mass that disagrees with the geometry invalidates
  the dimensional sheet rather than adding one more finding to it.
- Rejecting a part that measures the drawn limit. The limit is the
  drawing's, not the subtraction's, and a strict comparison against a
  computed bound refuses good hardware on some machines and accepts it
  on others.
- Recording an out-of-band diode as a rework item. The part cannot be
  cut back, so the state is what gets reported and the layout, not the
  diode, is what has to move.

## Behavior contract (gate 3)

The policy validation, band limits and feature states, deviation
fractions, footprint area, contact coverage and current density, the
diametrical true-position combination and worst-point selection, the
implied-mass crosscheck and the dimensional verdict are exercised by
the gate 3 contract test:
scripts/test_e2008_protection_diode_dimensions_weight.py against
scripts/e2008_protection_diode_dimensions_weight_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_protection_diode_dimensions_weight.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
