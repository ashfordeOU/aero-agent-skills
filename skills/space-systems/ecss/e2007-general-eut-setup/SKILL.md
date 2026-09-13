---
name: e2007-general-eut-setup
description: "Use when verify that a tested unit is arranged in the standard laboratory configuration required by ECSS-E-ST-20-07C clause 5.2.6.1 before emission or susceptibility measurements start: categorize every bench item as tested-unit, support-equipment, interconnecting-harness or coupling-network, check the insulating-standoff height and dielectric, the setback from the reference-plane front edge, the shielded-enclosure wall clearance, the reference-plane area against the unit footprint plus perimeter-margin, and the exposed harness length and routing height, then hold the run until every geometric non-conformance is closed. Trigger: ecss, e-st-20-electrical-scope, tested-unit-layout, laboratory-configuration, reference-plane-bench, insulating-standoff, harness-routing-geometry, shielded-enclosure-clearance, setup-readiness-gate."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-general-eut-setup, tested-unit-layout, laboratory-configuration, reference-plane-bench, insulating-standoff, harness-routing-geometry]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Test Setup — General Tested-Unit Arrangement (space-systems/ecss/e2007-general-eut-setup)

Use when the task is the ECSS-E-ST-20-07C clause 5.2.6.1 arrangement of a
tested unit in the standard laboratory configuration before an
electromagnetic measurement -- categorizing every item on the bench,
checking the placement geometry against the configuration envelope, and
holding the run while any geometric non-conformance is open.

## Domain quick reference

- Reproducibility across laboratories comes from geometry, not from
  instrumentation alone. The same unit measured 100 mm and 400 mm back
  from the reference-plane edge, or 50 mm and 200 mm above it, produces
  different coupling and different results, so the arrangement is fixed
  and recorded before the first reading.
- Every bench item is categorized by its role before it is placed:
  exactly one tested unit, support equipment that stimulates, loads or
  monitors it, the interconnecting harness, and the coupling networks
  feeding the unit. A role outside that set has no defined place in the
  standard arrangement and is rejected rather than guessed at.
- The tested unit sits on an insulating standoff of controlled height
  above a conductive reference plane. The standoff carries two
  requirements, not one: the height band, and a low relative
  permittivity so the standoff itself does not load the coupling path.
  A relative permittivity below unity is physically impossible and is a
  data error, not a good result.
- The reference plane must cover the unit footprint plus a perimeter
  margin on all four sides; the required area is the footprint grown by
  twice the margin in each direction. A plane smaller than that puts the
  plane edge inside the measurement.
- Two distinct clearance families apply: two-sided bands, where the
  measured value must sit inside a tolerance around a nominal (standoff
  height, front-edge setback, exposed harness length, routing height),
  and one-sided floors, where the value must merely reach a minimum
  (enclosure wall clearance, item separation).
- The exposed harness run has a nominal length and a nominal height above
  the plane; the remainder is stowed. An exposed run longer than the
  harness itself is an impossible input and is rejected outright.

## Workflow

1. Categorize the bench: map every item role to tested unit, support
   equipment, interconnecting harness or coupling network. Reject an
   unrecognized role, a duplicate item name, an empty bench, or a bench
   that does not hold exactly one tested unit.
2. Compute the required reference-plane area from the tested-unit
   footprint and the perimeter margin, and compare it with the plane
   actually available on the bench.
3. Run the two-sided band checks: standoff height, front-edge setback,
   exposed harness length and harness routing height, each against its
   nominal and tolerance from the arrangement specification.
4. Run the one-sided floor checks: shielded-enclosure wall clearance and
   separation between the tested unit and adjacent items.
5. Check the standoff dielectric against the permitted relative
   permittivity, independently of the height band.
6. Confirm an interconnecting harness is actually on the arrangement
   record; a geometry check that never sees the harness has not checked
   the dominant coupling path.
7. Aggregate the findings and emit the gate token. Only an empty finding
   list releases the bench for measurement; anything else holds the
   setup.

## Pitfalls

- Treating the arrangement as a checklist run after the first sweep. Once
  a reading exists, moving the unit to satisfy the geometry invalidates
  the reading, so the arrangement is closed first.
- Checking the standoff height and calling the standoff compliant. Height
  and dielectric are two independent requirements, and a high-permittivity
  block at exactly the right height still changes the coupling.
- Sizing the reference plane to the unit footprint. The margin is needed
  on all four sides, so the required area grows by twice the margin in
  each direction, not once.
- Confusing a band with a floor. Enclosure wall clearance larger than the
  minimum is fine; an exposed harness run longer than nominal is not,
  because the harness length sets the coupling length.
- Accepting an exposed harness run longer than the harness. That is a
  data-entry error that would otherwise propagate into a negative stowed
  length and a silently wrong geometry record.
- Recording only the tested unit and calling the bench categorized. The
  support equipment and coupling networks share the plane and set the
  separations that the arrangement is supposed to fix.
- Letting a stack-up sum that lands a few units in the last place outside
  a band read as a non-conformance. The logic absorbs representation
  error with a named tolerance far below any millimetre value; the band
  itself is never widened.

## Behavior contract (gate 3)

The bench categorization, band and floor checks, reference-plane sizing,
standoff, harness-routing and readiness-gate logic is exercised by the
gate 3 contract test: `scripts/test_e2007_general_eut_setup.py` against
`scripts/e2007_general_eut_setup_logic.py` (stdlib unittest, offline).
Run: python3 scripts/test_e2007_general_eut_setup.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
