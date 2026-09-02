---
name: document-control
description: "Use when you must control aerospace manufacturing documents: maintain the master list of controlled documents, check that a document is approved before issue, confirm that the shop floor copy is at the current revision, and disposition obsolete revisions by removing them from active use while retaining them in the register as history. Produces the register validity verdict, the use verdict for a copy, and the obsolete disposition that gate document control. Trigger: document control, master list, controlled document, current revision, obsolete revision, revision control, approval before issue, doc number."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: as9100
    reference-only: true
gated: false
domain: manufacturing-quality
pack: manufacturing-quality
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: manufacturing-quality
  subdomain: as9100
  tags: [document-control, revision-control, master-list, current-revision, controlled-document, obsolete-revision, approval-before-issue, doc-number]
  version: 0.1.0
  author: Aero Agent Skills
---

# Document Control (manufacturing-quality/as9100/document-control)

Use when the task is controlling manufacturing documents per AS9100
practice: the master list tracks every controlled document, approval
precedes issue, the shop floor works from the current revision, and
obsolete revisions leave active use but stay in the register as
history.

## Domain quick reference

- A controlled document lives in the master list with a doc number,
  title, revision, issue date, status (draft, issued, obsolete),
  author, and approver.
- Approval before issue: the approver must be recorded and must not
  be the author (independent approval); drafts need no approval.
- register_validity returns 'valid' or a reason: missing-doc-number,
  missing-title, missing-revision, missing-issue-date,
  unknown-status, missing-approval.
- Revision identifiers are uppercase single letters (A, B, C) or
  positive integers (1, 2, 3); a mixed pair raises ValueError in
  revision_compare.
- use_verdict classifies a copy in use: current, superseded
  (older revision or obsolete status), unreleased (draft),
  future-revision (ahead of the master list).
- master_list_check(entries, doc_number, revision) matches the exact
  doc number and revision pair and returns the use verdict for that
  listed copy; an unlisted pair is not controlled.
- current_revision returns the highest issued revision in the master
  list for a doc number; draft and obsolete entries never count.
- obsolete_action disposes an obsolete revision: remove from active
  use, mark status obsolete, retain in the register as history.
- AS9100 frames document control as part of the QMS infrastructure;
  the register model here is a practical summary, not clause text.

## Workflow

1. Record the document in the master list with doc_number, title,
   revision, issue_date, status, author, and approver.
2. Check the entry with register_validity; fix missing fields or
   missing approval before issue.
3. Confirm the approver is independent with approval_ok.
4. Verify the copy in use with use_verdict(entry, current_revision)
   or master_list_check(entries, doc_number, revision); the verdict
   must be current.
5. Find the master-list revision with current_revision and compare
   it against the shop floor copy.
6. When a revision goes obsolete, apply obsolete_action: remove
   from active use, keep in the register as history.

## Pitfalls

- Issuing without approval: an issued entry with no approver, or
  with the author approving their own document, fails as
  missing-approval.
- Mixed revision identifiers: comparing a letter revision with an
  integer revision raises ValueError; a consistent register uses one
  scheme.
- Draft copies in production: a draft copy yields unreleased and must
  not be used for manufacturing.
- Obsolete copies left in circulation: an obsolete entry always
  yields superseded, never current; remove it from active use.
- Unlisted documents: a doc number and revision pair absent from the
  master list is not controlled; master_list_check returns unlisted
  instead of guessing.
- Deleting history: obsolete revisions are retained in the register,
  not destroyed.

## Behavior contract (gate 3)

The document control logic is exercised by the gate 3 contract test:
scripts/test_document_control.py against
scripts/document_control_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_document_control.py

## Compliance

- Standards referenced, not reproduced: AS9100 document control is
  summarized as a register model and workflow, common aerospace
  quality practice per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
