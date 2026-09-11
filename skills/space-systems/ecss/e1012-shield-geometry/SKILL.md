---
name: e1012-shield-geometry
description: "Use when build the radiation shielding geometry model for a component
  or equipment item under ECSS-E-ST-10-12C §6.3: assemble the three-tier shielding
  hierarchy (parts packaging, equipment housing, spacecraft structure), compute the
  areal density contribution of each shielding layer, sum contributions across all
  tiers to derive the effective shielding seen by the sensitive part, and check
  interfaces (connectors, cutouts, feed-throughs) where the local effective shielding
  falls below a required minimum threshold. Trigger: ecss, e-st-10-12c,
  shield-geometry, areal-density, radiation-shielding, parts-packaging,
  equipment-shielding, spacecraft-structure."
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
  tags: [ecss, e-st-10-12c, shield-geometry, areal-density, radiation-shielding, parts-packaging, equipment-shielding, spacecraft-structure]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Environment — Radiation Shielding Geometry (space-systems/ecss/e1012-shield-geometry)

Use when the task is to build the radiation shielding geometry model for a
sensitive part under ECSS-E-ST-10-12C §6.3 — defining the three-tier shielding
hierarchy, computing areal density per tier, summing total effective shielding,
and verifying that every interface meets the minimum shielding threshold.

## Domain quick reference

- §6.3 organises the shielding seen by a sensitive part into three tiers from
  inner to outer: **parts packaging** (die encapsulant, ceramic or metallic
  package body, lid), **equipment** (PCB substrate, ground plane, box walls,
  cover plate, heatsink), and **spacecraft** (structural panels,
  inter-equipment shielding plates, external walls). Each tier is independent
  and its contribution is summed to obtain the total effective shielding.
- The fundamental quantity for each shielding layer is **areal density**
  (g/cm²) = physical thickness (cm) × material bulk density (g/cm³). Areal
  density is the conserved quantity across materials: aluminium, steel,
  tantalum, and titanium layers with the same areal density stop approximately
  the same fluence of electrons and protons for the purposes of a simplified
  shielding analysis.
- **Interfaces** — connectors, cable feed-throughs, apertures, access covers,
  and cutouts — interrupt the normal shielding continuity of the tier they
  belong to. Each interface must be inventoried and assigned its own effective
  areal density (typically much lower than the surrounding wall). An interface
  whose effective areal density is below the programme-level minimum threshold
  must be flagged as a shielding gap.
- A sensitive part whose total effective shielding (summed across all tiers) is
  below the programme-level minimum must also be flagged, separately from any
  interface finding.

## Workflow

1. Identify the sensitive part and its location within the equipment. Record the
   reference point at the part's geometric centre.
2. For each tier (parts packaging, equipment, spacecraft), list every material
   layer that interposes between the reference point and the space environment.
   For each layer record: name, material, physical thickness (cm), and bulk
   density (g/cm³).
3. Compute the areal density of each layer: thickness (cm) × density (g/cm³).
   Sum the layer areal densities within each tier to obtain the tier
   contribution.
4. Sum the three tier contributions to obtain the total effective shielding in
   g/cm². Compare the total against the programme-level minimum threshold; flag
   a shortfall as a shielding-deficiency finding.
5. Inventory all interfaces associated with each tier. For each interface,
   record its effective areal density (the shielding remaining through the
   interface aperture, including any local reinforcement). Compare each
   interface against the minimum interface threshold; flag any interface below
   the threshold as a shielding-gap finding.
6. Collect all findings (shielding-deficiency and shielding-gap) for the
   sensitive part. The part's shielding geometry is considered compliant only
   when the finding list is empty for both deficiency and gap checks.

## Pitfalls

- Omitting the parts-packaging tier because it appears small — ceramic package
  bodies (density ≈ 3.9 g/cm³, thickness ≈ 0.05–0.1 cm) contribute 0.2–
  0.4 g/cm², which is comparable to a thin aluminium box wall and must not be
  ignored.
- Treating all interfaces as having zero shielding — a connector backshell or
  feed-through ferrule does provide a non-zero areal density; assign the
  correct value rather than assuming worst case, to avoid masking genuine gaps
  elsewhere.
- Applying a single minimum threshold to both the total effective shielding and
  the interface threshold — the two limits derive from different requirements
  (total dose vs. point-of-entry single-event) and are programme-specific
  inputs, not the same number.
- Summing the tiers without first verifying that the layer densities are bulk
  material values (not porous, not composite average) — composite or honeycomb
  panels require the effective density to be computed from the actual
  solid-fraction geometry before converting to areal density.

## Behavior contract (gate 3)

The layer-creation, areal-density summation, geometry-model assembly,
interface-check, and validation logic is exercised by the gate 3 contract
test: scripts/test_e1012_shield_geometry.py against
scripts/e1012_shield_geometry_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1012_shield_geometry.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
