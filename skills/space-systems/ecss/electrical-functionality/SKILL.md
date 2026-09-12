---
name: electrical-functionality
description: "Use when assess electrical conductivity, lightning protection, and EMC provisions on spacecraft structure under ECSS-E-ST-32C clauses 4.3.10–4.3.12: check each structural joint's bonding resistance against the applicable limit for primary or secondary structure, assign every external surface to a lightning protection zone and confirm that zone-appropriate provisions are present, and verify EMC structural-bonding resistance and aperture controls meet requirements. The procedure flags joints that exceed the bonding resistance threshold, surfaces that lack a zone assignment or required lightning protection provisions, and apertures that are unscreened above the structural shielding cutoff frequency. Trigger: ecss, e-st-32c-structures-scope, electrical-conductivity, bonding-resistance, lightning-protection, lightning-zone, emc-provisions, structural-bonding, aperture-control, shielding."
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
  tags: [ecss, e-st-32c-structures-scope, electrical-conductivity, bonding-resistance, lightning-protection, lightning-zone, emc-provisions, structural-bonding, aperture-control, shielding]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Electrical Functionality (space-systems/ecss/electrical-functionality)

Use when the task is assessing the electrical conductivity, lightning
protection, and EMC provisions of spacecraft structure under
ECSS-E-ST-32C clauses 4.3.10–4.3.12: checking structural joint
bonding resistance, confirming lightning protection zone assignments
and provisions, and validating EMC structural-bonding resistance and
aperture controls.

## Domain quick reference

- Clause 4.3.10 (electrical conductivity) requires structural joints
  to maintain electrical continuity within defined resistance limits:
  primary load-bearing joints must not exceed 2.5 mΩ; secondary
  structural joints must not exceed 10 mΩ. These thresholds prevent
  resistive heating at joints and ensure the structure forms a
  coherent ground reference.
- Clause 4.3.11 (lightning protection) requires every external
  surface to carry a lightning protection zone assignment (zones 1A,
  1B, 2A, 2B, or 3), based on the probability and nature of lightning
  attachment, and to be equipped with the provisions appropriate to
  that zone: zone 1A (frequent direct attachment) requires strike
  receptors, down conductors, and diverter strips; zone 1B (occasional
  direct attachment) requires strike receptors and down conductors;
  zones 2A and 2B (swept stroke) require down conductors and/or
  diverter strips; zone 3 (interior, no direct attachment) requires no
  external provisions.
- Clause 4.3.12 (EMC provisions) requires the structure to provide a
  continuous low-impedance ground plane: all structural bonds used for
  EMC continuity must not exceed 2.5 mΩ, and apertures in the
  structural shell wider than 30 mm must be fitted with conductive
  screening mesh with openings no larger than 3 mm to prevent
  unwanted RF coupling through the structural shell.

## Workflow

1. Inventory all structural joints and record the structure class
   (primary or secondary) and measured or predicted bonding resistance
   for each joint. Joints without a recorded resistance are findings
   before any limit check is performed.
2. For each joint, compare the bonding resistance against the limit
   for its structure class (2.5 mΩ primary, 10 mΩ secondary). Record
   whether the joint is within the limit and compute the resistance
   margin. Joints exceeding the limit require a corrective bond strap
   or surface treatment.
3. Inventory all external surfaces and confirm that each carries a
   lightning protection zone assignment. External surfaces without an
   assigned zone are findings independent of the provision check.
4. For each external surface with a zone assignment, verify that all
   provisions required by that zone are present. Record any missing
   provisions per surface.
5. For all structural bonds designated as part of the EMC ground
   plane, apply the EMC bonding resistance limit of 2.5 mΩ. Bonds
   that pass the structural bonding check may still fail the EMC check
   if they are secondary-class joints (limit 10 mΩ structural vs.
   2.5 mΩ EMC).
6. Inventory all apertures (access panels, pass-throughs, ventilation
   slots) in the structural shell. For each aperture wider than 30 mm,
   confirm a conductive screen is fitted and that the mesh opening
   does not exceed 3 mm. Flag unscreened apertures and screens with
   openings above the limit.
7. Aggregate all findings across the three areas; a structure is
   electrically compliant only when the findings lists for bonding,
   lightning protection, and EMC are all empty.

## Pitfalls

- Applying the secondary-structure bond limit (10 mΩ) to joints in
  the EMC ground plane — EMC continuity requires the same 2.5 mΩ
  limit that applies to primary structural bonds, regardless of the
  structural class of the joint.
- Treating an internal surface's missing zone assignment as a finding
  — the lightning protection zone requirement applies only to external
  surfaces that can receive a lightning attachment or swept stroke;
  internal surfaces are not in scope.
- Recording a large aperture as adequately screened because a mesh is
  present without verifying the mesh opening size — a coarse mesh
  (> 3 mm) provides insufficient attenuation and the aperture must be
  treated as unscreened.
- Checking only the most safety-critical joints and assuming the rest
  are compliant — every joint in the inventory must be checked; a
  single non-compliant joint breaks the ground-plane continuity.

## Behavior contract (gate 3)

The bonding resistance, lightning zone assignment, lightning
provision, EMC bonding, and aperture control logic is exercised by
the gate 3 contract test:
scripts/test_electrical_functionality.py against
scripts/electrical_functionality_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_electrical_functionality.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
