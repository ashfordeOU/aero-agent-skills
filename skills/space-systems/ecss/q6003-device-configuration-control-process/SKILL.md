---
name: q6003-device-configuration-control-process
description: "Determine how a proposed change to an established device baseline must be categorised, routed and evidenced under ECSS-Q-ST-60-03C clause 8.3, aligned with ECSS project-management change practice. Use when a change request is open against a functional, design or product baseline and the supplier needs to know which board dispositions it, what the package must carry, and whether it may be worked yet. Sorts the change on its declared impacts, names the approval authority, lists absent evidence, reports work done before disposition, and returns the baseline version an approved change yields. Trigger: ecss, q-st-60-03, device-baseline-change-control, change-category-first-or-second, customer-change-board-routing, change-impact-assessment, device-baseline-version-increment, disposition-before-implementation."
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
  tags: [ecss, q-st-60-device-assurance-scope, q6003-device-configuration-control-process, device-baseline-change-control, change-category-first-or-second, customer-change-board-routing, device-baseline-version-increment, change-impact-assessment]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Assurance — Baseline Change Control (space-systems/ecss/q6003-device-configuration-control-process)

Use when the task is the change-control step of ECSS-Q-ST-60-03C clause
8.3 — taking a proposed change to a device baseline and deciding what
category it is, who dispositions it, what has to be in the package and
whether it may be implemented yet.

## Domain quick reference

- Change control starts at a baseline, not at a design. A proposal
  raised before any baseline was established is a design decision being
  made for the first time; treating it as a change invents an approval
  record that has nothing under it, so an unestablished baseline is
  refused as an input error.
- The category follows the reach of the impact, not the size of the
  edit. An impact that leaves the supplier — form, fit or function, an
  external interface, qualification evidence, the delivered
  documentation baseline, the criticality category, or a committed cost
  or schedule — makes the change first category however small the edit
  is. A change whose whole effect stays inside the supplier's own
  implementation and process stays second category however large it is.
- The category decides the route. A first-category change is
  dispositioned by the customer change board because the customer owns
  what it touches; a second-category change stays with the supplier
  configuration board. The route is derived, never chosen.
- The package scales with the category and with the baseline stage.
  Both categories need an impact assessment and an updated item data
  list; a first-category change adds a re-verification plan, the list of
  affected deliverables and the customer notification record. Once the
  baseline is a product baseline, hardware exists against it, so any
  category also needs the assessment of what happens to the units
  already built.
- Order is part of control. Implementation follows disposition, and
  disposition follows raising. Work done before the disposition date, or
  with no disposition at all, is an uncontrolled change even when the
  board later approves the same content.
- The baseline moves only when the change is actually implementable. A
  first-category change opens a new major baseline; a second-category
  change advances the minor. A rejected, deferred or still-open change
  leaves the version exactly where it was.

## Workflow

1. Validate the baseline: stage, version in major-minor form, and the
   established flag. Refuse a change against a baseline that was never
   established.
2. Normalise the declared impact set against the closed impact
   vocabulary; an unrecognised impact is an input error, not a silent
   internal one.
3. Categorise the change and keep the impacts that triggered the first
   category, so the review can see exactly why it routed outward.
4. Derive the approval authority from the category.
5. Build the demanded evidence set from the category and the baseline
   stage, and list what the package does not carry.
6. Check the date order of raising, disposition and implementation, and
   report each ordering defect separately.
7. Allow implementation only on an approved disposition with a complete
   package and a clean order; then compute the resulting baseline
   version, leaving it unchanged when implementation is not allowed.

## Pitfalls

- Categorising on effort. A one-line edit that changes an external
  interface is first category; a substantial internal rework that
  changes nothing outside the supplier is second. Sizing the change
  tells you nothing about its route.
- Choosing the board. The authority is a consequence of the category;
  routing a first-category change to the supplier board because it is
  quicker removes the customer from a decision they own.
- Treating a product-stage change like a design-stage one. Units already
  exist, so the package needs a statement about them; without it an
  approved change leaves built hardware in an undefined state.
- Accepting an approval that arrived after the work. The content may be
  identical, but the period between implementation and disposition was
  uncontrolled and belongs in the findings.
- Advancing the baseline version on approval alone. Approval with an
  incomplete package or an out-of-order record does not make the change
  implementable, and a version bump then claims a baseline that nothing
  supports.
- Folding a deferred change into the rejected ones. Deferred keeps the
  proposal alive against the same baseline; rejected closes it, and the
  two lead to different next actions.

## Behavior contract (gate 3)

The baseline validation, impact normalisation, category decision,
authority routing, stage-dependent evidence set, date-order checks, the
implementation gate and the baseline increment are exercised by the gate
3 contract test:
scripts/test_q6003_device_configuration_control_process.py against
scripts/q6003_device_configuration_control_process_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6003_device_configuration_control_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
