---
name: e1011-workstations
description: "Use when assess workstation layout and human-factors design for a crewed spacecraft under ECSS-E-ST-10-11C §4.7.6: verify display placement within acceptable viewing angles from the crew Eye Reference Point, verify controls fall within the reach envelope for their access-frequency zone (primary, secondary, or tertiary), and verify ingress/egress clearance dimensions meet minimum crew-access requirements. Categorize each workstation element by access-frequency zone, flag any element outside its zone's viewing or reach limits, and confirm every access path meets clearance minimums. Trigger: ecss, e-st-10-system-scope, e-st-10-11c, workstation, human-factors, viewing-angle, reach-envelope, ingress-egress, layout."
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
  tags: [ecss, e-st-10-system-scope, e-st-10-11c, workstation, human-factors, viewing-angle, reach-envelope, ingress-egress, layout]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Human Factors — Workstation Design (space-systems/ecss/e1011-workstations)

Use when the task is verifying that a crewed spacecraft workstation meets
the layout, viewing, reach, and ingress/egress requirements of
ECSS-E-ST-10-11C §4.7.6. Each workstation element (display, control, access
path) is categorized by its access-frequency zone and checked against the
dimensional limits for that zone.

## Domain quick reference

- §4.7.6 requires that every display and control be categorized into an
  access-frequency zone before its placement is assessed. A **primary zone**
  element is accessed frequently during normal operations and must lie within
  the preferred field of view and functional reach. A **secondary zone**
  element is accessed occasionally and may extend to the acceptable field of
  view and maximum reach. A **tertiary zone** element is for reference or
  emergency use only and is expected to require crew repositioning to access.
- **Viewing** is assessed from the crew Eye Reference Point (ERP) — the
  design eye position at the 95th-percentile seated or restraint eye height.
  Both horizontal and vertical angles from the ERP to each display centre are
  checked independently against the zone limits. Viewing distance is also
  bounded: too short causes eye strain, too long degrades readability. Primary
  zone limits are tighter than secondary zone limits to ensure critical
  displays are readable without head rotation.
- **Reach** is assessed from the Shoulder Reference Point (SRP). Each zone
  has a maximum reach radius: primary zone controls must lie within functional
  reach (achievable without body lean), secondary zone controls within maximum
  reach (allowing a lean but not repositioning). Tertiary zone elements carry
  no fixed radius because repositioning is already expected and accepted for
  that zone.
- **Ingress/egress** clearances (clear width and clear height of the access
  path to the workstation) are checked against three access modes: normal
  operational, maintenance, and emergency egress. Emergency egress has the
  smallest minimum width to accommodate suited crew in a time-critical
  scenario; normal operational has the tallest minimum height for unrestricted
  upright passage.

## Workflow

1. Record the workstation identifier and the design-anthropometry Eye
   Reference Point (ERP) and Shoulder Reference Point (SRP) positions.
2. Categorize each display and control by access-frequency zone: primary,
   secondary, or tertiary. Reject any element with an unrecognized zone label
   before proceeding to placement assessment.
3. For each display, compute the horizontal angle (deviation from the
   straight-ahead sightline) and the vertical angle (deviation from
   horizontal, negative = below) from the ERP to the display centre, and
   measure the viewing distance from ERP to display surface. Compare each
   value against the zone's viewing limits; record a finding for every
   exceedance.
4. For each control, compute the reach distance from the SRP to the control
   actuation point. Compare it against the zone's maximum reach radius; record
   a finding if the control exceeds its zone's limit. Tertiary zone controls
   require no reach check — they are already accepted as needing repositioning.
5. For each ingress/egress access path to the workstation, record the clear
   width, clear height, and access mode (normal operational, maintenance, or
   emergency egress). Compare width and height against the minimums for that
   mode; record a finding for each shortfall.
6. Aggregate display, reach, and access-path findings for the workstation; the
   workstation design satisfies §4.7.6 only when all three finding lists are
   empty.

## Pitfalls

- Skipping the zone categorization step and applying primary zone limits
  uniformly overstates non-compliance for secondary elements placed at the
  wider secondary limits and may miss primary elements placed too far away.
- Using the 50th-percentile body dimensions instead of the anthropometric
  design drivers: 5th-percentile female drives reach limits (smallest reach
  must still reach the control), 95th-percentile male drives clearance limits
  (largest body must still clear the passage).
- Checking only horizontal viewing angle and ignoring vertical angle — a
  display located far below the ERP sightline can pass the horizontal check
  but require excessive neck flexion, which §4.7.6 prevents via the vertical
  limit.
- Applying the emergency-egress minimum width to all access-path checks — the
  normal-operational minimum is wider and applies to all non-emergency checks.
  Using the smaller emergency figure as a universal baseline allows
  non-compliant designs to pass.

## Behavior contract (gate 3)

The zone-categorization, viewing-angle, reach-envelope, and access-path logic
is exercised by the gate 3 contract test:
scripts/test_e1011_workstations.py against scripts/e1011_workstations_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e1011_workstations.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
