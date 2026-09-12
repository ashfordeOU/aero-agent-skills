---
name: lightning-protection-verification
description: "Use when verify lightning-protection compliance of a spacecraft or launch vehicle structure under ECSS-E-ST-32C clause 4.6.3.25: assign each external and transition region to a strike zone (direct attachment, swept stroke, or protected), measure and compare structural bond resistance against class-specific limits, trace the lightning-current path for continuity across all bonded segments, confirm shielding coverage on Zone A and Zone B surfaces, and validate that all bonding strap and fastener inspection records are complete and conformant. Trigger: ecss, e-st-32c, e-st-32-structures-scope, lightning-protection, bond-resistance, strike-zone, shielding-continuity, structural-bonding, grounding-verification."
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
  tags: [ecss, e-st-32c, e-st-32-structures-scope, lightning-protection, bond-resistance, strike-zone, shielding-continuity, structural-bonding, grounding-verification]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Lightning-Protection Verification (space-systems/ecss/lightning-protection-verification)

Use when the task is the lightning-protection verification test and inspection of
ECSS-E-ST-32C clause 4.6.3.25 — assigning strike zones to all external and
transition regions, verifying structural bond resistance against class limits,
confirming current-path continuity, checking shielding coverage on exposed zones,
and validating inspection records for all bonding straps and fasteners.

## Domain quick reference

- Clause 4.6.3.25 requires that every external and transition region of the
  structure be assigned to one of three strike zones before any verification
  measurement is taken. Zone A covers regions subject to direct lightning
  attachment (first and last attachment points). Zone B covers regions subject
  to a swept stroke (the channel sweeps along the surface as the vehicle moves).
  Zone C covers interior and protected regions with no direct channel contact.
  Each zone drives different shielding and bonding requirements, so a region
  assigned to the wrong zone invalidates all downstream checks.
- Bond resistance is the primary measured quantity. Each structural bond joint
  is assigned a bond class that sets its allowable resistance limit: primary
  bonds (main lightning-current path through the outer structure) must not
  exceed 2.5 mΩ; secondary bonds (sub-structure connections) must not exceed
  10.0 mΩ; equipment bonds (equipment enclosures connected to structure) must
  not exceed 25.0 mΩ. A measurement that exceeds the class limit is a
  non-conformance regardless of margin on adjacent joints.
- Current-path continuity is verified by tracing the intended lightning-current
  path from a representative strike attachment point through each bonded segment
  to the exit ground reference. Every segment in the path must independently
  pass its bond-class resistance check; a single failing segment breaks the
  path and renders the entire route non-compliant.
- Shielding coverage requires that every surface in Zone A or Zone B either
  carries a verified shielding layer (metallic skin, conductive coating, or
  bonded mesh) or is confirmed non-critical by analysis. A composite surface
  in Zone A or Zone B without a documented shielding disposition is a finding
  even if the bond resistance of adjacent joints is compliant.
- Inspection completeness requires a documented inspection record for every
  bonding strap and fastener in the verified assembly. An uninspected strap
  is a finding regardless of the resistance measurement at that joint, because
  the physical condition of the strap (corrosion, mechanical damage, missing
  hardware) is not captured by a resistance-only test.

## Workflow

1. Retrieve the lightning strike zone map for the structure and assign each
   external and transition region to Zone A, Zone B, or Zone C. Reject any
   region with a missing or unrecognized zone assignment before proceeding;
   an unassigned region cannot be verified.
2. For each bond joint in the verified assembly, record the measured resistance
   in milliohms and the bond class (primary, secondary, or equipment). Apply
   the class resistance limit and record PASS or FAIL with the numeric margin.
   Reject a record with an unrecognized bond class; do not assume a default
   limit.
3. Trace the lightning-current path from each Zone A attachment point through
   the bonded segment chain to the ground reference. For each segment, confirm
   it already appears in the bond-resistance check results with a PASS outcome.
   A segment absent from the results, or present with a FAIL outcome, breaks
   the path.
4. For each surface in Zone A or Zone B, confirm that a shielding disposition
   is on record (shielded or confirmed non-critical by analysis). A surface
   with no disposition record is a shielding finding even if bond resistance
   is compliant.
5. For each bonding strap and fastener in the assembly, confirm an inspection
   record exists and is marked complete. Flag any item with a missing or
   incomplete record.
6. Aggregate findings: a surface or path is fully compliant only when the bond
   resistance check passes for every joint, the current path is unbroken, the
   shielding disposition is resolved, and all inspection records are complete.
   Partial compliance is not compliance.

## Pitfalls

- Verifying bond resistance without first assigning strike zones — the bond
  class limits and shielding requirements differ by zone, so measurements taken
  before zone assignment can produce a false pass on joints that are actually
  primary-zone joints requiring a tighter limit.
- Treating a chain of passing joints as a passing current path without
  explicitly tracing the path — a joint can pass its individual resistance
  check while being absent from the intended current path entirely, leaving a
  break at a different segment that was never measured.
- Accepting a shielded-surface entry as compliant without confirming the
  shielding layer is bonded into the current path — a shielding layer that is
  electrically isolated from the structure provides no conduction path and is
  not compliant even if it is physically present.
- Reading a missing inspection record as "no finding" — the inspection record
  is an independent conformance check from the resistance measurement; its
  absence is a finding in its own right, not a neutral state.
- Applying the secondary-bond limit (10.0 mΩ) to a joint on the primary
  lightning-current path because the joint is structurally minor — bond class
  is determined by position in the current path, not by structural significance.

## Behavior contract (gate 3)

The strike-zone assignment, bond-resistance check, current-path continuity,
shielding-coverage, and inspection-record logic is exercised by the gate 3
contract test: scripts/test_lightning_protection_verification.py against
scripts/lightning_protection_verification_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_lightning_protection_verification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
