---
name: e2040-device-definition-phase-review
description: "Evaluate whether the definition phase may close and architecture work start, the gate ECSS-E-ST-20-40C clause 5.2.7 places there: check each data item the phase owes against the maturity this gate demands rather than against mere presence, stop on an open major review discrepancy, and accept a discrepancy with an action only when that action falls due before the work it is meant to protect begins. Use when a definition-phase review package is assembled or chaired, or when a gate decision is reconstructed afterwards. Trigger: ecss, e-st-20-electrical-scope, device-definition-phase-review, definition-gate-data-item-maturity, review-discrepancy-disposition, action-due-before-architecture-start, definition-gate-verdict."
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
  tags: [ecss, e-st-20-electrical-scope, e2040-device-definition-phase-review, device-definition-phase-review, definition-gate-data-item-maturity, review-discrepancy-disposition, action-due-before-architecture-start, definition-gate-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Requirements — Definition Phase Review (space-systems/ecss/e2040-device-definition-phase-review)

Use when the task is the gate duty of ECSS-E-ST-20-40C clause 5.2.7 --
deciding whether the definition phase is closed and architecture work on
the device may begin, from the package submitted and the discrepancies
raised against it.

## Domain quick reference

- The gate has a fixed package: the requirements specification, the
  development plan, the pre-tailoring matrix, the preliminary
  verification plan and the feasibility and risk assessment. A data item
  the phase owes and did not submit is a gate stopper, not a gap to note.
- Maturity is per item, not one bar across the package. The requirements
  specification and the tailoring matrix have to be baselined because
  the architecture is about to be built against them; a plan may still
  sit at for-review. A package counted by presence passes with drafts
  inside it.
- A data item with no revision cannot be identified later. The gate
  reviewed something; a year on nobody can say what.
- Discrepancy severity decides the disposition that is allowed. An open
  major discrepancy stops the gate. An open minor or editorial one is
  carried as an action.
- A discrepancy accepted with an action is a conditional pass only while
  the action falls due BEFORE the work it constrains starts. An action
  due after architecture work has begun protects nothing it was raised
  to protect, and an action with no due date is not an action.
- A major discrepancy simply rejected needs a recorded rationale. The
  disposition alone records a decision with no reasoning behind it.
- Closure ratios are counts over counts, so a threshold met exactly is
  met and the comparison absorbs representation error.

## Workflow

1. Fold the package onto the data items the phase owes, refusing a
   repeat or an unknown key as an input defect, and report every item
   the package does not carry.
2. Compare each submitted item against the maturity THIS gate requires
   for that item, and report an item with no revision separately.
3. Fold every discrepancy onto a severity and a disposition, refusing a
   repeated identifier.
4. Stop the gate on an open major discrepancy; carry an open minor or
   editorial one as an action.
5. For each discrepancy accepted with an action, require a due date and
   require it to fall before architecture work starts.
6. Report a rejected major discrepancy as needing a rationale.
7. Compute the closure ratio, compare it against any declared threshold
   absorbing representation error, and return the verdict: not-closed on
   any blocking finding, closed-with-actions when something is carried,
   closed otherwise.

## Pitfalls

- Counting the package by presence. Five items are on the table and two
  of them are drafts; the gate passes and the architecture is built
  against a requirements specification that is still moving.
- Applying one maturity bar to every item. It either blocks plans that
  are legitimately at for-review or lets the specification through as a
  draft, and both are wrong in the same review.
- Accepting an action with no due date, or with one after the phase it
  was meant to protect. The discrepancy is recorded as dispositioned and
  reappears, unchanged, at the next gate.
- Treating an open minor discrepancy as a stopper. It converts a
  conditional pass into a schedule hit for an editorial point.
- Comparing a closure ratio against its threshold with a strict
  inequality. A two-of-two division landing on 1.0 can sit a unit in the
  last place below it and red a gate that closed everything.

## Behavior contract (gate 3)

The package folding, per-item maturity comparison, revision check,
discrepancy folding, disposition rules, action due-date placement
against the architecture start and the closure-threshold comparison are
exercised by the gate 3 contract test:
scripts/test_e2040_device_definition_phase_review.py against
scripts/e2040_device_definition_phase_review_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2040_device_definition_phase_review.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
