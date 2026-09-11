---
name: e1002-rod-report
description: "Use when produce or audit a review-of-design report against the ECSS-E-ST-10-02 clause 5.3.2.3 and Annex D Document Requirements Definition: confirm the review panel exists and is independent of the design authors by identity rather than by declaration, confirm every reviewed document is pinned to a revision, confirm each checklist item carries a result with an adverse item dispositioned and a not-applicable item justified, and close the review only when nothing adverse remains open. Trigger: ecss, e-st-10-02c, review-of-design, annex-d-drd, reviewer-independence, checklist-disposition, document-revision, design-evidence."
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
  tags: [ecss, e-st-10-02c, review-of-design, annex-d-drd, reviewer-independence, checklist-disposition, document-revision]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Verification — Review-of-Design Report DRD (space-systems/ecss/e1002-rod-report)

Use when the verification method is review of design under
ECSS-E-ST-10-02 clause 5.3.2.3 and Annex D -- where the evidence is
documentary, and its worth depends entirely on who looked, at what
revision, against what checklist.

## Domain quick reference

- Independence is the property that makes this method work. A designer
  reviewing their own drawing reads what they meant rather than what
  they drew, so the review returns the design's own assumptions.
- Independence is checked by identity against the design authors, never
  by a declaration in the report. A report can describe a review as
  independent while the reviewer signed the drawing.
- A partially conflicted panel and a wholly conflicted one are different
  findings. One names the individual to swap out; the other says the
  review has no independent view in it at all and must be redone.
- Every reviewed document is pinned to a revision. A review of an
  unversioned document cannot be repeated, and says nothing at all
  after the next change to that document.
- Each checklist item carries a result. An adverse item carries a
  disposition, because an unsatisfactory finding with no decision
  attached is an observation that closes nothing.
- A not-applicable item carries a justification. Without it,
  "not applicable" is the cheapest way to make a checklist pass.
- The verdict turns on disposition, not on count: an item accepted or
  waived closes, an item with an action still raised leaves the review
  open. A review with an open action has not finished, however few they
  are.
- A report that reviewed no documents at all is reported explicitly; an
  empty document set otherwise passes every per-document check
  vacuously.

## Workflow

1. Confirm reviewers are assigned, then check each against the design
   author list; report conflicted individuals and a wholly conflicted
   panel separately.
2. Confirm every reviewed document carries a pinned revision, and that
   at least one document was reviewed.
3. For each checklist item, confirm a result; for an adverse result
   confirm a valid disposition; for not-applicable confirm a
   justification.
4. Derive the verdict: open while any adverse item is neither accepted
   nor waived, closed otherwise.
5. The evidence is acceptable only when the review closed with no
   finding standing.

## Pitfalls

- Accepting a report's own statement that the review was independent.
  The check is the reviewer roster against the author roster.
- Treating one independent reviewer on a conflicted panel as sufficient
  without naming the conflicts; the conflicted members still shaped the
  discussion.
- Listing reviewed documents by title only. At the next revision nobody
  can say what was actually examined.
- Closing a review with actions still raised, on the grounds that they
  are tracked elsewhere. Tracked is not dispositioned.
- Marking items not applicable to clear a checklist, with no
  justification recorded for any of them.
- Running every per-document check over an empty document set and
  reporting a clean review that examined nothing.

## Behavior contract (gate 3)

The independence, reviewer-panel, document-revision, checklist-result,
disposition and verdict logic is exercised by the gate 3 contract test:
scripts/test_e1002_rod_report.py against
scripts/e1002_rod_report_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1002_rod_report.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
