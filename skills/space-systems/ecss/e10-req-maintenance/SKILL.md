---
name: e10-req-maintenance
description: "Use when maintaining ECSS-E-ST-10C requirements under configuration control (clause 5.2.3.8): determine whether a requirement's lifecycle state transition (draft, proposed, baselined, obsolete) is allowed, verify that a change to a baselined requirement carries an approved change request before it is applied, assess the change's impact on derived requirements found via the parent-child traceability link and on verification items linked to the requirement, and confirm the impact assessment and a maintenance record are captured before the change is closed. Trigger: ecss, e-st-10c, requirement maintenance, configuration control, change impact assessment, derived requirements, verification impact, baseline change request."
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
  tags: [ecss, e-st-10c, requirement-maintenance, configuration-control, change-impact-assessment, traceability, verification-impact]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS System Engineering — Requirement Maintenance (space-systems/ecss/e10-req-maintenance)

Use when the task is maintaining requirements under configuration
control per ECSS-E-ST-10C clause 5.2.3.8 -- checking that a
requirement's lifecycle state transition is allowed, that a change to
a baselined requirement is backed by an approved change request, and
that the change's impact on derived requirements and linked
verification items has been assessed and recorded before the change
is closed.

## Domain quick reference

- A requirement moves through four lifecycle states: draft (freely
  editable), proposed (under review), baselined (under configuration
  control), and obsolete (terminal, superseded or withdrawn). Only
  specific transitions are allowed: draft -> proposed or obsolete;
  proposed -> draft (rejected back to authoring), baselined, or
  obsolete; baselined -> obsolete; obsolete has no outgoing
  transition. Any other pair is a disallowed transition.
- Configuration control applies once a requirement is baselined: a
  baselined requirement's content may only be modified alongside an
  approved change request. A draft or proposed requirement is not yet
  under configuration control and can be edited directly.
- A requirement change has two possible ripple effects that must be
  traced before the change is closed: derived requirements (children
  linked to the changed requirement through the parent-child
  traceability record) that may need re-derivation or re-review, and
  verification items (test, analysis, review, or inspection activities
  linked to the requirement) that may need re-verification. Either
  list can be empty for a given requirement, but a nonempty list means
  the impact is real and must be assessed, not just discovered.
- A closed change on a baselined requirement leaves two records: the
  impact assessment (what was checked, evaluated against the
  traceability and verification links) and the maintenance record
  (the change history entry itself). Both are separate from the
  approved-change-request gate that authorizes touching the baseline
  in the first place.

## Workflow

1. Confirm the requirement's current lifecycle state is a recognized
   one (draft, proposed, baselined, obsolete) and that the intended
   target state is reachable by an allowed transition; reject a
   transition that is not on the allowed list.
2. If the requirement is being modified and its current state is
   baselined, confirm an approved change request is on record before
   proceeding; flag the change if the requirement is baselined and
   under modification without one.
3. Look up the requirement's derived requirements via the parent-child
   traceability link and its linked verification items; this is the
   change impact assessment for the requirement.
4. If either the derived-requirement list or the verification-item
   list is nonempty, confirm the change record documents that the
   impact was assessed; flag a missing impact assessment when there is
   real impact but no assessment recorded.
5. If the requirement is baselined and being modified, confirm a
   maintenance record (change history entry) exists; flag its absence.
6. Aggregate the configuration-control, impact-assessment, and
   maintenance-record findings; the change is not maintenance-compliant
   until all three lists are empty.

## Pitfalls

- Allowing an edit to a baselined requirement because "it's a small
  change" without an approved change request -- clause 5.2.3.8 gates
  on configuration-control status, not change size; baselined always
  requires the change request.
- Treating an empty derived-requirements list as proof no impact
  assessment is needed on the verification side, or vice versa --
  the two impact channels are independent; a requirement can have
  linked verification items with no derived children, or the reverse.
- Recording the change history entry and calling the change complete
  without a documented impact assessment -- the maintenance record and
  the impact assessment are separate artifacts; having one does not
  imply the other was done.
- Skipping the lifecycle transition check for a requirement moving
  straight from draft to baselined, or from obsolete back to any other
  state -- both are disallowed transitions under this leaf's model and
  must be rejected before any configuration-control or impact logic
  runs.

## Behavior contract (gate 3)

The lifecycle-transition, configuration-control, change-impact-
assessment, and maintenance-record logic is exercised by the gate 3
contract test: scripts/test_e10_req_maintenance.py against
scripts/e10_req_maintenance_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e10_req_maintenance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
