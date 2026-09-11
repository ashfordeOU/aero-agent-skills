---
name: e1002-other-reports
description: "Use when decide whether a verification activity needs documentation beyond the four report DRDs under ECSS-E-ST-10-02 clause 5.3.2.6, and check what is produced: derive the need from the activity's own trigger conditions rather than preference, confirm any additional report carries the minimum identification that makes it citable, confirm its author did not also approve it, and flag a report that restates the scope of a DRD report already produced for the same activity. Trigger: ecss, e-st-10-02c, additional-documentation, verification-reporting, trigger-conditions, report-duplication, self-approval, citability."
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
  tags: [ecss, e-st-10-02c, additional-documentation, verification-reporting, trigger-conditions, report-duplication]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Verification — Additional Verification Documentation (space-systems/ecss/e1002-other-reports)

Use when the task is to decide whether a verification activity needs
documentation beyond the four report DRDs under ECSS-E-ST-10-02 clause
5.3.2.6 -- and to check that whatever is produced earns its place.

## Domain quick reference

- The clause is permissive, and that is precisely why it needs a
  decision rule. Left to preference it fails in both directions: no
  record where one was genuinely needed, and reports that restate a DRD
  report already covering the activity.
- The need is derived from the activity's circumstances -- a campaign
  spanning facilities, work performed by a supplier, a test-analysis
  correlation, an invoked deviation, reused heritage evidence, one
  activity across several articles. Any one of these makes a record
  necessary.
- Triggers are reported in a declared order so the same activity always
  produces the same answer, whatever order the flags were written in.
- Duplication is a finding, not diligence. Two documents describing one
  activity will eventually disagree, and the verification control
  document then cannot say which governs.
- Duplication counts only against DRD reports actually produced. An
  additional report covering ground a DRD report *could* have covered,
  but did not, is carrying real content.
- An additional report still needs the minimum identification that makes
  it citable from the verification control document: its own
  identifier, the requirements it bears on, the activity, an author and
  an approver. A record nothing can cite is not part of the
  verification argument.
- An empty list where content is required -- no requirement references
  at all -- is the same defect as an absent field.
- Author and approver must differ. Self-approval removes the second pair
  of eyes that makes an out-of-DRD record worth citing at all.

## Workflow

1. Read the activity's trigger conditions and derive whether an
   additional report is required.
2. If required and none exists, report that directly against the
   activity.
3. For each additional report, check the minimum identification fields,
   treating an empty list as missing.
4. Confirm the author is not also the approver.
5. Compare the report's declared scope against the DRD reports actually
   produced for the activity and flag any overlap.
6. The documentation is sufficient only when nothing is missing,
   duplicative or uncitable.

## Pitfalls

- Leaving the decision to judgement, which produces both silent gaps and
  redundant paperwork on the same programme.
- Writing an additional report that re-narrates the test report, so two
  records of one activity drift apart over the next two revisions.
- Flagging overlap against a DRD report that was never produced,
  suppressing a document that is in fact carrying the only record.
- Filing a report with no requirement references, which cannot be
  reached from the verification control document and so never enters
  the argument.
- Letting the engineer who ran the activity approve their own account of
  it.
- Treating an empty requirement list as present because the field
  exists.

## Behavior contract (gate 3)

The trigger-derivation, missing-report, minimum-field, self-approval and
duplication logic is exercised by the gate 3 contract test:
scripts/test_e1002_other_reports.py against
scripts/e1002_other_reports_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1002_other_reports.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
