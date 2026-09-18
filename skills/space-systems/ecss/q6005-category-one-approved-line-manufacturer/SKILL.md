---
name: q6005-category-one-approved-line-manufacturer
description: "Determine whether a hybrid source qualifies for the preferred category one route of ECSS-Q-ST-60-05 clause 5.2.1: confirm the part is built on the very line the approval names, test that approval for currency at the procurement day, admit an approval still in progress only while its application is lodged, and audit the process identification document against every content item the clause mandates. Use when a hybrid source is categorized before an order is placed, when a line move is proposed mid-programme, or when an approval is running out. Reports the category decision, days to lapse, the document gap set and a completeness figure. Trigger: ecss, q-st-60-05c-clause-5-2-1, category-one-hybrid-manufacturer, approved-hybrid-production-line, pending-hybrid-line-approval, hybrid-process-identification-document, hybrid-pid-content-audit, hybrid-line-approval-expiry."
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
  tags: [ecss, q-st-60-eee-scope, q6005-category-one-approved-line-manufacturer, category-one-hybrid-manufacturer, approved-hybrid-production-line, pending-hybrid-line-approval, hybrid-process-identification-document, hybrid-line-approval-expiry]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrid Procurement — Category One Approved-Line Manufacturer (space-systems/ecss/q6005-category-one-approved-line-manufacturer)

Use when the task is the clause 5.2.1 source decision of ECSS-Q-ST-60-05:
a hybrid is being bought and the question is whether its maker sits in the
preferred case, where the part comes off a production line that already
carries an approval — or an approval in progress — and where a process
identification document describes that line with the content the clause
mandates. The decision is about a line and a document, not about a company
name.

## Domain quick reference

- The approval attaches to a production line, not to the manufacturer. A
  plant can hold an approved line and run the hybrid on a second one; the
  second line has no approval, so the part is outside the preferred case
  even though the maker's letterhead is unchanged. Line identity is
  therefore compared after normalization for case, spacing and separator,
  and any residual difference is a real difference.
- Two approval states carry a part into the preferred case: an approval in
  force, and an approval whose application is lodged and still open. The
  remaining states — lapsed, withdrawn, never sought — are the category two
  conversation, held under clause 5.2.2, not a weaker version of this one.
- An approval in force is bounded by a date. A line whose approval expired
  last month is not an approved line, and the question at the procurement
  day is how many days remain, not whether the certificate was ever issued.
  Expiry falling on the assessment day still counts as in force.
- The process identification document is the thing that makes the approval
  reviewable: the line it names, the materials and parts it consumes, the
  process flow and its sequence, the die-attach and interconnection
  parameters, sealing and encapsulation, the screening and qualification
  flow, in-process controls, change control and the traceability scheme. A
  document that omits one of these is not a shorter document; it is a
  document whose gap has to be named before the line can be leaned on.
- Content the document declares outside the mandated set is a signal that
  the wrong document has been supplied, so it is refused rather than
  silently ignored.

## Workflow

1. Validate the source record: the maker, the line the hybrid is actually
   built on, the line the approval was granted against, the approval state
   and the dates that bound it. An approved line with no expiry, or an
   application-pending line with no application date, is an input error.
2. Normalize both line identities and compare them. A mismatch is recorded
   as its own finding, naming both lines, so the buyer can see whether the
   fix is a line move or an approval extension.
3. Decide approval currency at the procurement day: days remaining for an
   approval in force, and for a pending case whether the application
   predates the assessment. Report the day count rather than a bare verdict.
4. Audit the process identification document against the mandated content
   list. Return the gap set in mandated order plus a completeness figure,
   never a single pass or fail.
5. Accumulate every finding — the findings do not short-circuit, because a
   buyer needs the whole repair list, not the first blocker.
6. Return the category decision. The preferred route holds only when the
   state is admissible, the approval is current, the build line matches and
   the document has no gap.

## Pitfalls

- Reading the approval as belonging to the manufacturer. It belongs to one
  line; a build moved to a sister line in the same plant leaves the
  preferred case until that line is covered too.
- Treating an application in progress as equivalent to an approval in
  force without checking that the application is actually lodged. An
  application dated after the assessment day evidences nothing yet.
- Accepting a process identification document on its title page. The clause
  mandates content, so the audit is item by item and the missing items are
  reported by name.
- Answering the document audit with a yes or no. The completeness figure
  and the gap set are what a supplier acts on; a bare refusal tells them
  nothing about how far off they are.
- Stopping at the first finding. A lapsed approval, a moved line and a
  document gap are three separate repairs and are reported together.
- Reading an expiry landing exactly on the assessment day as lapsed. The
  comparison is on whole days and zero days remaining is still in force.

## Behavior contract (gate 3)

The record validation, line-identity normalization, approval-currency
decision, process identification document audit and the category decision
itself are exercised by the gate 3 contract test:
scripts/test_q6005_category_one_approved_line_manufacturer.py against
scripts/q6005_category_one_approved_line_manufacturer_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6005_category_one_approved_line_manufacturer.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
