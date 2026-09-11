---
name: e1003-management
description: "Use when manage a system-level test campaign under ECSS-E-ST-10C §4.3.1: assign customer and supplier responsibilities to each test event, verify that all mandatory readiness conditions (configuration baseline locked, procedure approved, support-equipment calibrated, personnel qualified, safety clearance granted) are satisfied before authorising a test, sequence campaign phases from planning through closeout, and flag any responsibility gap or unmet readiness prerequisite before the test-readiness review is held. Trigger: ecss, e-st-10-system-scope, test-management, test-campaign, readiness-review, customer-supplier, test-responsibility, test-readiness."
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
  tags: [ecss, e-st-10-system-scope, test-management, test-campaign, readiness-review, customer-supplier, test-responsibility]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS System Testing — Test Campaign Management (space-systems/ecss/e1003-management)

Use when the task is to organise a system-level test campaign per
ECSS-E-ST-10C §4.3.1 — assigning responsibilities between customer and
supplier, verifying test readiness before a run is authorised, and
sequencing campaign phases in the required order.

## Domain quick reference

- §4.3.1 partitions test-campaign responsibilities into two roles.
  The **customer** owns witness decisions, procedure approval sign-off,
  and final acceptance of test results. The **supplier** conducts tests,
  prepares and executes procedures, controls the test environment, and
  maintains the configuration baseline. Some events (system integration,
  combined operations) are joint — both parties share responsibility for
  planning and execution.
- Readiness conditions are mandatory prerequisites that must each be
  confirmed true before a test is authorised to start. The five canonical
  conditions are: configuration baseline locked; test procedure approved;
  support equipment calibrated and within validity; personnel qualified for
  the test; safety clearance granted. A test with any unmet condition is
  not authorised — partial satisfaction does not suffice.
- Campaign phases follow a fixed sequence: planning → preparation →
  readiness review → execution → reporting → closeout. Phases may be
  tailored out (omitted) when formally justified, but the relative order of
  retained phases must not be changed.

## Workflow

1. Inventory every test event in the campaign and record its test type
   (acceptance, unit, subsystem, environmental, manufacturing, system,
   integration, combined operations, or qualification witness). Reject any
   event whose type is not on the recognised list before it enters the
   responsibility assignment step.
2. For each event, apply the responsibility rule: acceptance and
   qualification-witness tests are customer-led; unit, subsystem,
   environmental, and manufacturing tests are supplier-led; system,
   integration, and combined-operations tests are joint. Record the
   assigned role and flag any event where the assignment could not be made
   automatically (unknown type or contested override).
3. Before each test, evaluate all five mandatory readiness conditions.
   Collect which conditions are confirmed and which remain unmet. A single
   unmet condition blocks authorisation. Record unknown or ad-hoc condition
   labels as warnings — they do not satisfy the canonical list.
4. Assemble the campaign phase sequence and validate it against the
   canonical order. Flag out-of-order phases, unknown phase names, and
   duplicates; do not proceed to execution review if the sequence is invalid.
5. Build the campaign plan: aggregate responsibility assignments and
   readiness status across all events. The campaign is ready to enter
   execution only when every event carries a valid responsibility assignment
   and all readiness conditions are met for each event.

## Pitfalls

- Treating partial readiness as sufficient — all five conditions must be
  confirmed; an event that satisfies four of five is not authorised.
- Allowing an unrecognised test type to pass through without an explicit
  responsibility decision — unknown types must be resolved or rejected before
  the campaign plan is finalised.
- Reordering campaign phases to work around scheduling pressure — the
  readiness review must precede execution; bypassing it invalidates the
  authorisation chain.
- Conflating the customer witness role with joint responsibility — a customer
  witness test is customer-led (supplier conducts, customer witnesses and
  accepts); that is not the same as a joint event where both parties share
  planning and execution responsibility.

## Behavior contract (gate 3)

The responsibility-assignment, readiness-condition, phase-sequencing, and
campaign-plan logic is exercised by the gate 3 contract test:
scripts/test_e1003_management.py against scripts/e1003_management_logic.py
(stdlib unittest, offline). Run:

    python3 scripts/test_e1003_management.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
