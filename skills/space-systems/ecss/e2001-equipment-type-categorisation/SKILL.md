---
name: e2001-equipment-type-categorisation
description: "Use when determine the multipactor type-group that one item of radio-frequency hardware falls into under ECSS-E-ST-20-01C clause 4.4.1, and read the applicable multipactor-margin off it: tier the gap-geometry from uniform-waveguide through printed-line and non-uniform-assembly to dielectric-loaded, tier the secondary-emission surface knowledge from flight-surface-measured through process-coupon-sample to unknown, take the worse of the two tiers, add the design-heritage adder, roll an assembly up to its most demanding constituent, and flag every declared group or declared margin the derived policy does not support. Trigger: ecss, e-st-20-electrical-scope, e2001-equipment-type-categorisation, multipactor-type-group, gap-geometry-tier, secondary-emission-surface-knowledge, design-heritage-adder, assembly-rollup-grouping, equipment-component-grouping."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-equipment-type-categorisation, multipactor-type-group, gap-geometry-tier, secondary-emission-surface-knowledge, design-heritage-adder, assembly-rollup-grouping]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipaction — Equipment Type Categorisation (space-systems/ecss/e2001-equipment-type-categorisation)

Use when the task is the sorting step of ECSS-E-ST-20-01C clause 4.4.1 --
putting each piece of radio-frequency hardware into the type-group that
governs which multipactor-margin applies to it, before any breakdown
calculation is attempted.

## Domain quick reference

- The group is not a label of convenience: it is the input that fixes the
  margin. Getting the group wrong understates the margin for the rest of the
  campaign, and no later analysis recovers it.
- Two properties decide the group, and they are independent. The first is how
  well the gap-geometry confines the field. A uniform-waveguide or a
  coaxial-line has one well-defined gap with a near-homogeneous field. A
  printed-line has fringing edges where the local field departs from the
  nominal. A radiating-aperture or a non-uniform-assembly (multiplexer,
  switch matrix, multi-cavity filter) presents many gaps, each with its own
  field shape. A dielectric-loaded part adds surfaces that charge, so its
  breakdown behaviour is the least predictable of the four.
- The second property is how well the emitting surface is known:
  flight-surface-measured (secondary-emission data taken on the actual
  surface treatment), process-coupon-sample (data from a coupon of the same
  process), or unknown-surface.
- Each property maps to a tier, 1 for the best known and 4 for the least. The
  item takes the worse of the two tiers -- confidence in one property never
  offsets ignorance in the other, so the tiers are compared, never averaged.
- The tier fixes a base multipactor-margin, and design heritage adds to it: a
  recurrent build of qualified hardware adds nothing, a modified recurrent
  build adds one decibel, a new design adds two. Heritage moves the margin, it
  does not move the group.
- An assembly is categorized from its own properties and from its
  constituents. It inherits the worst constituent tier and the largest
  constituent margin, and the item that set them is named so the number can be
  traced back to the part responsible.
- A declared group that is more demanding than the derived one is still a
  finding: it is conservative, but it points at a policy the inventory does
  not actually justify, and conservative labels applied by hand tend to drift.

## Workflow

1. List every component and every equipment assembly in scope. Give each an
   identifier, a gap-geometry family, a surface-knowledge state, a heritage
   state, and for an assembly the identifiers of its constituents.
2. Reject the inventory before any grouping when a family, a surface state, a
   heritage state or a kind is unrecognised, when an identifier repeats, or
   when a component declares constituents.
3. Map gap-geometry and surface-knowledge to their tiers and take the worse
   of the two. Record which of the two properties governed -- that is the
   property to attack if the margin has to come down.
4. Read the base margin off the tier and add the heritage adder to get the
   applicable multipactor-margin for the item.
5. Roll each assembly up: compare its own tier and margin against every
   constituent, keep the worst, and name the governing item.
6. Audit whatever the item declared about itself. Flag a declared group that
   sits below the derived one as understated, a declared group above it as
   overstated, and a declared margin short of the derived policy value,
   absorbing representation error with a named tolerance rather than relaxing
   the policy.
7. Report the per-group counts, the most demanding item in the inventory and
   the finding list; the inventory is consistent only when that list is empty.

## Pitfalls

- Averaging the two tiers, or letting excellent surface data pull a
  dielectric-loaded part into a lower group. The worse property governs.
- Grouping an assembly on its housing and ignoring the one dielectric-loaded
  window or printed-line board inside it. The roll-up exists precisely because
  the worst constituent sets the margin for the whole unit.
- Treating heritage as a group change. A recurrent build of a
  non-uniform-assembly is still a non-uniform-assembly; heritage only moves
  the adder.
- Using process-coupon-sample data as if it were flight-surface-measured
  because the coupon came from the same shop. The tier difference is exactly
  the uncertainty between the coupon and the flight part.
- Carrying a hand-declared group forward without deriving it. The declared
  value is a claim; the derived value from geometry and surface knowledge is
  the one the margin should follow.
- Reading a comfortable margin on a group-1 component and applying it to the
  assembly that contains it.

## Behavior contract (gate 3)

The tiering, group derivation, margin policy, assembly roll-up and declaration
audit logic is exercised by the gate 3 contract test:
scripts/test_e2001_equipment_type_categorisation.py against
scripts/e2001_equipment_type_categorisation_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2001_equipment_type_categorisation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
