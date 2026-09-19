---
name: e3102-qualification-stage-quality-audits
description: "Structure the qualification stage of a two-phase heat transport development and grade the supplier-process quality audits it depends on, per ECSS-E-ST-31-02C clauses 5.5.1 and 5.5.2. Use when the task is ordering the stage activities so a process audit closes before the qualification model is manufactured, working out which declared processes are special processes that owe an audit at all, judging whether an audit is still inside its validity window and was run by an auditor independent of the audited organisation, and deciding whether an open major finding holds the stage at its entry gate. Trigger: ecss, e-st-31-02c, qualification-stage-structure, supplier-process-quality-audit, special-process-audit-coverage, audit-validity-window, auditor-independence, open-major-finding-block."
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
  tags: [ecss, e-st-31-02-two-phase-scope, e3102-qualification-stage-quality-audits, qualification-stage-structure, supplier-process-quality-audit, special-process-audit-coverage, audit-validity-window, auditor-independence]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Two-Phase Heat Transport — Qualification Stage and Quality Audits (space-systems/ecss/e3102-qualification-stage-quality-audits)

Use when the task is the qualification stage of ECSS-E-ST-31-02C clauses
5.5.1 and 5.5.2 -- laying out the stage activities in an order that means
something, and establishing that the supplier processes the stage rests on
have been audited recently enough, independently enough and cleanly enough
to be relied on.

## Domain quick reference

- The stage has a fixed spine: the qualification plan is approved, the
  supplier's processes are audited, the qualification model is
  manufactured, the test campaign runs, and the qualification review
  closes it. The order is not administrative. An audit run after the
  model is built can only describe how the model was already made; it
  cannot change it, so the audit's whole purpose -- catching a process
  defect before it is baked into the article under test -- is lost.
- Not every process owes an audit. The ones that do are the special
  processes, where conformity cannot be established by inspecting the
  finished article: closure welding, brazing, wick sintering, groove
  extrusion, cleaning and passivation, fluid purity and charging, heat
  treatment, non-destructive inspection and leak testing. A torque
  operation is verifiable on the delivered item; a sintered wick's pore
  structure and a charged fluid's purity are not.
- An audit is evidence with a shelf life. Personnel, tooling and work
  instructions drift, so an audit older than the stated validity window
  no longer describes the process as it is run today, and a stale audit
  is treated exactly like a missing one.
- Independence is part of the evidence, not a formality. An audit of an
  organisation by itself cannot produce the finding that embarrasses it,
  so a non-independent audit contributes no coverage however recent and
  however clean it reads.
- Findings separate by severity. An open major finding is an unresolved
  process defect and blocks entry to the test campaign; open minor
  findings are tracked and reported but do not hold the gate. Counting
  them together either blocks on paperwork or waves through a real defect.
- Where a process has several audits the most recent one governs. An
  older clean audit sitting behind a recent one with an open major
  finding is history, not coverage.

## Workflow

1. Validate each audit record: a named process, an integer project month,
   an explicit independence flag and non-negative finding counts. A
   missing field is an input error, not an assumed zero.
2. Reduce the declared process list to the special processes that owe an
   audit, normalising names so a spelling difference is not read as a
   different process.
3. Keep the most recent audit per process and grade it: expired when its
   age exceeds the validity window, not-independent when the auditor was
   not independent, open-major-finding when a major finding is still
   open, covered otherwise. An age exactly equal to the window is still
   inside it.
4. Build the coverage picture over the required processes, with an
   absent record recorded as missing rather than silently dropped, and
   reduce it to a coverage fraction.
5. Grade the planned sequence against the stage precedences, reporting
   both an absent activity and an inverted pair.
6. Assemble the blocking findings -- sequence violations plus every
   process whose audit is missing, expired, non-independent or carrying
   an open major finding -- and declare the stage ready only when that
   list is empty.
7. Report the open minor findings alongside the verdict so they are
   carried into the qualification review rather than lost.

## Pitfalls

- Auditing after the qualification model is built. The gate reads as
  closed and the audit exists, but it can no longer protect the article
  under test, and any process defect it finds is already inside the
  qualification evidence.
- Counting a non-special process towards coverage. Padding the
  denominator with operations that are verifiable on the delivered item
  makes a thin audit programme look broad.
- Treating an expired audit as partial credit. Validity is a threshold,
  not a gradient; a stale audit and a missing audit block the gate the
  same way.
- Accepting a self-audit because the report is detailed. Detail is not
  independence, and the finding that matters is the one the audited
  organisation had a reason not to write.
- Blocking on open minor findings, or letting a major one through with
  the minors. Severity is the whole point of the split; fold the two
  together and the gate stops discriminating.
- Letting an older clean audit stand for a process whose latest audit is
  bad. Coverage is about how the process is run now.

## Behavior contract (gate 3)

The audit-record validation, age and validity grading, independence and
finding severity handling, special-process reduction, coverage fraction,
sequence precedence check and readiness verdict are exercised by the gate
3 contract test:
scripts/test_e3102_qualification_stage_quality_audits.py against
scripts/e3102_qualification_stage_quality_audits_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e3102_qualification_stage_quality_audits.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
