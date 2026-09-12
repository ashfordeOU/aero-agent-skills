---
name: operations-and-maintenance
description: "Use when assess safe operating conditions, evaluate structural damage, derive maintenance intervals, or verify inspection findings for spacecraft and launch-vehicle structural systems per ECSS-E-ST-32 clause 4.2.3. Covers: computing maximum allowable operating pressure from proof-test constraints and safety factors, categorizing damage observations against allowable damage limits to produce accept/conditional/reject dispositions, scheduling maintenance from design-life and accumulated-cycle data, and confirming inspection measurements against acceptance tolerances. Trigger: ecss, e-st-32-structures-scope, operating-procedures, safe-pressure, damage-control, maintenance, inspection, allowable-damage-limit."
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
  tags: [ecss, e-st-32-structures-scope, operating-procedures, safe-pressure, damage-control, maintenance, inspection, allowable-damage-limit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Operations and Maintenance (space-systems/ecss/operations-and-maintenance)

Use when the task is establishing safe operating procedures, assessing
structural damage, scheduling maintenance, or verifying inspection outcomes
for spacecraft and launch-vehicle structural systems per ECSS-E-ST-32
clause 4.2.3.

## Domain quick reference

- **Safe operating pressure**: the maximum allowable operating pressure
  (MAOP) is the proof pressure divided by the applicable safety factor.
  ECSS-E-ST-32 clause 4.2.3 requires that no operating load or pressure
  exceed the MAOP; a positive margin means the operating value is below
  the limit, a zero margin is the boundary, and a negative margin is a
  violation requiring corrective action before operations resume.
- **Damage control**: observed damage (dent, scratch, crack, delamination,
  corrosion) is compared against the allowable damage limit (ADL) for that
  location and damage type. The ratio of observed size to ADL drives the
  disposition: at or below 75 % of ADL the item is accepted directly;
  between 75 % and 100 % the item enters a conditional-acceptance path
  requiring engineering review; above 100 % the item is rejected and
  must be repaired or replaced before return to service. No damage
  disposition is issued without a recorded ADL — a missing ADL is
  itself a finding.
- **Maintenance intervals**: design life is expressed in operating cycles
  (or calendar time). Maintenance is scheduled at a fixed fraction of
  design life; the next due point is the last inspection cycle plus that
  interval. A component whose next due point falls beyond design life
  must be retired or have its life formally extended before the due
  point is reached.
- **Inspection acceptance**: each inspection finding is one of the four
  types — dimensional, visual, torque, or pressure test. A measurement
  within the acceptance band (lower limit to upper limit inclusive)
  passes; outside either limit the finding fails and the component is
  withheld pending disposition.
- **Service life tracking**: accumulated cycles are compared against
  design life. Below 90 % of design life the status is in-service;
  from 90 % to 100 % the component is near its limit and triggers a
  life-extension review; above 100 % the component is expired and must
  be removed from service immediately.

## Workflow

1. Gather the component data record: proof pressure (or proof load),
   safety factor, design life in cycles, last inspection cycle, and the
   ADL table for each damage-susceptible location. Reject any assessment
   that proceeds without a recorded proof pressure or design life.
2. Compute the MAOP from proof pressure and safety factor. Compare the
   planned operating pressure or load against the MAOP and record the
   compliance margin. Flag any planned operation that would exceed the
   MAOP before it is authorized.
3. For each observed damage item, look up the ADL for that location and
   damage type. Compute the observed-to-ADL ratio and assign a
   disposition (accept, conditional, reject). Escalate conditional and
   rejected items to the responsible engineer before return to service.
4. Compute the next maintenance due cycle from the last inspection cycle
   and the interval fraction of design life. Confirm the due cycle does
   not exceed design life; if it does, flag a life-extension requirement
   before scheduling the next interval.
5. For each inspection finding, compare the measured value against the
   acceptance limits and record a pass or fail. Aggregate all findings;
   the component does not return to service until every finding is
   either passed or dispositioned.
6. Check the accumulated cycle count against design life. If the
   component is near its limit or expired, stop operations and initiate
   the life-extension or retirement process as applicable.

## Pitfalls

- Using proof pressure as the operating limit rather than dividing by
  the safety factor — the MAOP is always lower than proof pressure for
  any safety factor above 1.0; operating at proof pressure consumes the
  entire safety margin.
- Issuing a damage acceptance without a recorded ADL — a component with
  no ADL on file cannot be dispositioned; the absence of an ADL is
  itself a non-conformance, not a pass.
- Treating a conditional acceptance as equivalent to a direct accept —
  the conditional path requires a documented engineering review and
  approval before the component returns to service; skipping the review
  voids the disposition.
- Scheduling the next maintenance interval from the current date rather
  than from the last inspection cycle count — calendar drift decouples
  the schedule from actual usage and can allow overdue intervals to
  appear on-time.
- Continuing to operate a component whose accumulated cycle count has
  exceeded design life without a formal life-extension approval — design
  life expiry is an immediate stop-work condition under ECSS-E-ST-32.

## Behavior contract (gate 3)

The operating-pressure, damage-assessment, maintenance-interval,
inspection-finding, and service-life logic is exercised by the gate 3
contract test: scripts/test_operations_and_maintenance.py against
scripts/operations_and_maintenance_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_operations_and_maintenance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
