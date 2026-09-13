---
name: e2006-grounding-verification-by-inspection
description: "Use when verify that a spacecraft bonding-and-grounding provision is closed under ECSS-E-ST-20-06C clause 6.8.1 through inspection evidence combined with an electrical continuity measurement: categorize each provision as a structure-bond, equipment-chassis-bond, harness-shield-termination or static-dissipative-bleed-path, confirm the inspection record carries surface-preparation, fastener-installation, corrosion-protection and conductor-routing evidence with no open nonconformance, check the dc-bond-resistance reading was taken four-wire on an instrument that resolves the applicable bound, compare it against the per-category resistance bounds, and close the provision only when both halves pass and the network carries a structure-bond reference point. Trigger: ecss, e-st-20-06c, clause-6-8-1, grounding-provision-verification, bonding-continuity-inspection, dc-bond-resistance, four-wire-continuity-measurement, bond-strap-inspection-record, shield-termination-continuity, electrical-bonding-evidence."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-grounding-verification-by-inspection, grounding-provision-verification, bonding-continuity-inspection, dc-bond-resistance, shield-termination-continuity, four-wire-continuity-measurement]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Grounding Verification by Inspection (space-systems/ecss/e2006-grounding-verification-by-inspection)

Use when the task is the verification closure of ECSS-E-ST-20-06C clause
6.8.1 -- confirming that a bonding or grounding provision has both the
inspection evidence and the electrical continuity measurement on record
before it is declared verified.

## Domain quick reference

- Clause 6.8.1 makes verification a two-part obligation. Inspection
  alone proves a bond was built as drawn but not that it conducts;
  a continuity reading alone proves conduction at one instant but not
  that the joint was prepared, fastened and protected so it stays
  conductive. Neither half closes the provision on its own.
- Each provision is categorized before any bound applies. A
  structure-bond (face-to-face joint into primary structure) carries
  the tightest dc-bond-resistance bound; an equipment-chassis-bond and
  a harness-shield-termination carry progressively looser bounds; a
  static-dissipative-bleed-path is bounded on both sides -- too low is
  a short across the isolation, too high stops the surface bleeding.
  An uncategorized provision must never inherit a neighbouring
  category's bound.
- The inspection half records four attributes: surface-preparation
  (mask, finish, oxide removal at the mating faces), fastener-
  installation (correct hardware, washers, torque), corrosion-
  protection (sealing or finish restored after bonding) and
  conductor-routing (strap length, slack, bend radius). Only
  conductor-routing may be not-applicable, and only on a face-to-face
  structure-bond that has no strap.
- The electrical half is quality-gated, not just a number. A
  milliohm-level bound demands a four-wire dc reading -- a two-wire
  reading buries the joint in lead resistance -- and the instrument
  resolution must resolve the bound to at least one part in ten. A
  reading taken with an instrument that cannot resolve the bound is
  not evidence at any value.
- Network level: the bonds are measured against a reference. A
  dossier with no structure-bond reference point stays open even when
  every individual provision passes.

## Workflow

1. Categorize every provision in the dossier (structure-bond,
   equipment-chassis-bond, shield-termination, static-dissipative-
   bond), rejecting an unrecognized provision kind rather than
   defaulting it.
2. Evaluate the inspection record: all four attributes verified, the
   not-applicable state allowed only for conductor-routing on a
   face-to-face bond, and zero open nonconformances against the
   provision.
3. Evaluate the continuity measurement: method adequate for the
   bound, instrument resolution at or finer than one tenth of the
   bound, and the reading inside the category's lower/upper bounds.
4. Compute the fractional margin to the upper bound so a provision
   that passes with almost no margin is visible for retest after
   environmental exposure.
5. Close the provision only when both halves are clean; otherwise
   report it open with the inspection and continuity findings kept
   separate so the retest scope is unambiguous.
6. Roll up to the network: report open provisions, duplicate provision
   ids and a missing structure-bond reference point; the network is
   closed only when all three lists are empty.

## Pitfalls

- Accepting a continuity reading as full verification -- the clause
  pairs inspection with electrical testing, and a joint measured
  conductive over unprepared or unprotected faces will drift once it
  corrodes or relaxes.
- Reading a milliohm-level bond two-wire: the test-lead and contact
  resistance is of the same order as the bound itself, so the reading
  grades the leads, not the joint.
- Using an instrument whose resolution is coarse relative to the
  bound and treating the displayed value as a pass -- a reading that
  cannot resolve the bound carries no verification content whatever
  it displays.
- Marking surface-preparation or corrosion-protection not-applicable
  to clear a record; only conductor-routing has a legitimate
  not-applicable case, and only on a bond with no strap.
- Treating a static-dissipative-bleed-path as pass-if-low. It is
  bounded below as well as above; a near-short defeats the isolation
  the bleed path was added to preserve.
- Declaring the network verified from per-provision passes alone
  while no structure-bond reference point exists to measure against.

## Behavior contract (gate 3)

The categorization, inspection-record, continuity-measurement, margin
and network-closure logic is exercised by the gate 3 contract test:
scripts/test_e2006_grounding_verification_by_inspection.py against
scripts/e2006_grounding_verification_by_inspection_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2006_grounding_verification_by_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
