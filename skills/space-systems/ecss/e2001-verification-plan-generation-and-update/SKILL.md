---
name: e2001-verification-plan-generation-and-update
description: "Use when produce the multipactor-verification-plan required by ECSS-E-ST-20-01C clause 4.2.1 and keep it current afterwards: confirm the baseline plan is issued no later than the equipment-qualification-review and carries an approved sign-off rather than a draft state, validate the revision-history for unique identifiers and non-decreasing dates, categorize every configuration-change-event as one that forces a plan-update -- radio-frequency power increase, gap-geometry change, electrode-material change, multipactor-test-failure, analysis-margin erosion -- or one with no technical impact, measure how long each forcing event has stayed outside the plan against the agreed response-window, and trace every forcing event into the change-log before the plan counts as current. Trigger: ecss, e-st-20-electrical-scope, multipactor-verification-plan, equipment-qualification-review, plan-update-trigger, plan-revision-history, change-log-traceability, verification-plan-baseline."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-verification-plan-generation-and-update, multipactor-verification-plan, equipment-qualification-review, plan-update-trigger, plan-revision-history, change-log-traceability, verification-plan-baseline]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Multipactor Verification Plan Generation and Update (space-systems/ecss/e2001-verification-plan-generation-and-update)

Use when the task is the lifecycle of the multipactor-verification-plan
under ECSS-E-ST-20-01C clause 4.2.1 -- issuing the baseline plan by the
equipment-qualification-review and keeping it aligned with the design
afterwards. This leaf governs *when* the plan exists and *when* it has to
change; what the plan has to contain is a separate clause.

## Domain quick reference

- The plan is a milestone deliverable, not a running note. Its baseline
  is due no later than the equipment-qualification-review, because that
  review is where the equipment's qualification evidence is accepted --
  a plan written afterwards documents a campaign that already happened
  and can no longer steer it.
- "Issued" means two things at once: the right milestone *and* a
  released state. A plan sitting in draft or under-review at the
  equipment-qualification-review has not been issued, however good its
  content; conversely a plan approved late is approved, but the slip is
  itself a finding against the clause.
- The plan lives under configuration control after issue. Its revision
  history carries unique revision identifiers and non-decreasing issue
  dates; a revision dated before its predecessor means two branches of
  the document are circulating and the verification baseline is
  ambiguous.
- Not every project change touches the plan. A change is
  plan-update-forcing when it moves something the multipactor
  assessment rests on: the radio-frequency power at the equipment
  input, the geometry of a critical gap, an electrode material, the
  venting path, the susceptibility model, an agreed verification route,
  a granted waiver, the unit configuration, or a multipactor-test
  failure. Editorial corrections, reformatting, contact-detail updates
  and cross-reference renumbering are not.
- Currency is measured in two directions. Forward: a forcing event
  raised after the latest revision is pending, and pending beyond the
  agreed response-window is overdue. Backward: every forcing event has
  to appear in the plan's change-log, so an update that silently
  dropped an event is visible as a traceability gap rather than as a
  clean revision.

## Workflow

1. Validate the revision history: mappings with unique identifiers and
   parseable ISO dates that never step backwards. Reject the history
   rather than assess a plan whose baseline cannot be identified.
2. Resolve the milestone the plan was first issued at to its position
   in the project review sequence and compare it with the due
   milestone; report the slip in reviews, not a boolean alone.
3. Evaluate the release state against that comparison: draft and
   under-review are not issued; superseded means the wrong revision is
   in hand; approved-but-late is released with a finding.
4. Categorize every configuration-change-event as plan-update-forcing
   or of no plan impact, each with its recorded reason. An unrecognized
   event kind stops the assessment -- an event nobody can categorize
   cannot be shown to be harmless.
5. Select the pending updates: forcing events raised after the latest
   revision date. Count the days each has stayed open at the assessment
   date and mark those beyond the response-window as overdue. An event
   open exactly the window length is still inside it.
6. Trace the forcing events into the change-log and take the
   traceability fraction; a fraction landing exactly on the required
   minimum passes, the comparison absorbing representation error rather
   than relaxing the requirement.
7. Aggregate: the plan is compliant only when it was issued on time, is
   in a released state, has no pending or overdue update, and traces
   every forcing event.

## Pitfalls

- Reading a plan's date instead of its state. A document dated before
  the equipment-qualification-review but never approved is a draft, and
  treating its date as the issue closes the clause on evidence that
  does not exist.
- Treating "the plan exists" as the whole requirement. Clause 4.2.1 has
  two halves -- generation *and* update -- and a correctly issued plan
  that never absorbed the power increase raised three months later is
  the more common failure of the two.
- Categorizing a change by its paperwork rather than its physics. A
  change-request titled as a documentation update that moves an
  electrode material is plan-update-forcing; the trigger is what moved,
  not how it was raised.
- Counting only events after the latest revision. That finds pending
  updates but never finds the forcing event that was closed without
  reaching the change-log; the backward traceability pass is what
  catches it.
- Letting an unrecognized event kind default to harmless. Silent
  defaulting turns the one change nobody understood into the one change
  nobody assessed.
- Comparing milestones as strings. "qualification review" and
  "equipment qualification review" are different reviews in different
  places in the sequence, and a string match that collapses them moves
  the due date by several months.

## Behavior contract (gate 3)

The milestone resolution, baseline-issue evaluation, release-state
evaluation, revision-history validation, change-event categorization,
pending-update selection with the response-window boundary, change-log
traceability and the aggregated plan verdict are exercised by the gate 3
contract test: scripts/test_e2001_verification_plan_generation_and_update.py
against scripts/e2001_verification_plan_generation_and_update_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2001_verification_plan_generation_and_update.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
